package server

import (
	"bytes"
	"fmt"
	"net"
	"sync"
	"time"

	"github.com/fatedier/frp/models/msg"
	"github.com/fatedier/frp/utils/errors"
	"github.com/fatedier/frp/utils/log"
	"github.com/fatedier/frp/utils/pool"
	"github.com/fatedier/frp/utils/util"
)

// Timeout seconds.
var NatHoleTimeout int64 = 10

type NatHoleController struct {
	listener *net.UDPConn

	clientCfgs map[string]*NatHoleClientCfg
	sessions   map[string]*NatHoleSession

	mu sync.RWMutex
}

func NewNatHoleController(udpBindAddr string) (nc *NatHoleController, err error) {
	addr, err := net.ResolveUDPAddr("udp", udpBindAddr)
	if err != nil {
		return nil, err
	}
	lconn, err := net.ListenUDP("udp", addr)
	if err != nil {
		return nil, err
	}
	nc = &NatHoleController{
		listener:   lconn,
		clientCfgs: make(map[string]*NatHoleClientCfg),
		sessions:   make(map[string]*NatHoleSession),
	}
	return nc, nil
}

func (nc *NatHoleController) ListenClient(name string, sk string) (sidCh chan string) {
	clientCfg := &NatHoleClientCfg{
		Name:  name,
		Sk:    sk,
		SidCh: make(chan string),
	}
	nc.mu.Lock()
	nc.clientCfgs[name] = clientCfg
	nc.mu.Unlock()
	return clientCfg.SidCh
}

func (nc *NatHoleController) CloseClient(name string) {
	nc.mu.Lock()
	defer nc.mu.Unlock()
	delete(nc.clientCfgs, name)
}

func (nc *NatHoleController) Run() {
	for {
		buf := pool.GetBuf(1024)
		n, raddr, err := nc.listener.ReadFromUDP(buf)
		if err != nil {
			log.Trace("nat hole listener read from udp error: %v", err)
			return
		}

		rd := bytes.NewReader(buf[:n])
		rawMsg, err := msg.ReadMsg(rd)
		if err != nil {
			log.Trace("read nat hole message error: %v", err)
			continue
		}

		switch m := rawMsg.(type) {
		case *msg.NatHoleVisitor:
			go nc.HandleVisitor(m, raddr)
		case *msg.NatHoleClient:
			go nc.HandleClient(m, raddr)
		default:
			log.Trace("error nat hole message type")
			continue
		}
		pool.PutBuf(buf)
	}
}

func (nc *NatHoleController) GenSid() string {
	t := time.Now().Unix()
	id, _ := util.RandId()
	return fmt.Sprintf("%d%s", t, id)
}

func (nc *NatHoleController) HandleVisitor(m *msg.NatHoleVisitor, raddr *net.UDPAddr) {
	sid := nc.GenSid()
	session := &NatHoleSession{
		Sid:         sid,
		VisitorAddr: raddr,
		NotifyCh:    make(chan struct{}, 0),
	}
	nc.mu.Lock()
	clientCfg, ok := nc.clientCfgs[m.ProxyName]
	if !ok || m.SignKey != util.GetAuthKey(clientCfg.Sk, m.Timestamp) {
		nc.mu.Unlock()
		return
	}
	nc.sessions[sid] = session
	nc.mu.Unlock()
	log.Trace("handle visitor message, sid [%s]", sid)

	defer func() {
		nc.mu.Lock()
		delete(nc.sessions, sid)
		nc.mu.Unlock()
	}()

	err := errors.PanicToError(func() {
		clientCfg.SidCh <- sid
	})
	if err != nil {
		return
	}

	// Wait client connections.
	select {
	case <-session.NotifyCh:
		resp := nc.GenNatHoleResponse(raddr, session)
		log.Trace("send nat hole response to visitor")
		nc.listener.WriteToUDP(resp, raddr)
	case <-time.After(time.Duration(NatHoleTimeout) * time.Second):
		return
	}
}

func (nc *NatHoleController) HandleClient(m *msg.NatHoleClient, raddr *net.UDPAddr) {
	nc.mu.RLock()
	session, ok := nc.sessions[m.Sid]
	nc.mu.RUnlock()
	if !ok {
		return
	}
	log.Trace("handle client message, sid [%s]", session.Sid)
	session.ClientAddr = raddr
	session.NotifyCh <- struct{}{}

	resp := nc.GenNatHoleResponse(raddr, session)
	log.Trace("send nat hole response to client")
	nc.listener.WriteToUDP(resp, raddr)
}

func (nc *NatHoleController) GenNatHoleResponse(raddr *net.UDPAddr, session *NatHoleSession) []byte {
	m := &msg.NatHoleResp{
		Sid:         session.Sid,
		VisitorAddr: session.VisitorAddr.String(),
		ClientAddr:  session.ClientAddr.String(),
	}
	b := bytes.NewBuffer(nil)
	err := msg.WriteMsg(b, m)
	if err != nil {
		return []byte("")
	}
	return b.Bytes()
}

type NatHoleSession struct {
	Sid         string
	VisitorAddr *net.UDPAddr
	ClientAddr  *net.UDPAddr

	NotifyCh chan struct{}
}

type NatHoleClientCfg struct {
	Name  string
	Sk    string
	SidCh chan string
}
