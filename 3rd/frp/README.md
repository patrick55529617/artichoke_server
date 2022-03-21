# Frp Server

ARCHITECTURE amd64
VERSION 0.16.0
Dashboard modified

# ENV
bind_port		listen port
dashboard_port		Dashboard port
privilege_token		Token / Password
privilege_allow_ports	Allow ports
dashboard_user		User (Default: admin)
dashboard_pwd		Pass (Default: admin)

# Example
docker run -d \
    --name frps \
    --restart=always \
    --net=host \
    -e bind_port=7000 \
    -e dashboard_port=7500 \
    -e privilege_token=edt-1234 \
    -e privilege_allow_ports=7001-7499 \
    -e dashboard_user=edt \
    -e dashboard_pwd=edt-1234 \
    frps

# Frp Client (SSH)

ARCHITECTURE amd64
VERSION 0.16.0

# ENV
server_addr             Server IP/addr
server_port             Server port
user                    Name shows in dashboard (Default: EDT)
privilege_token         Token / Password
remote_port             Remote port             (Default: assign by server)

# VOL (not necessary)
/frp/username           Default name shows in dashboard

# Example 1: Set name by ENV
docker run -d \
    --name frpc \
    --restart=always \
    --net=host \
    -e server_addr=10.10.10.10 \
    -e server_port=7000 \
    -e user=$(hostname) \
    -e privilege_token=edt-1234 \
    -e remote_port=7001 \
    frpc

# Example 2: Set name by VOL
docker run -d \
    --name frpc \
    --restart=always \
    --net=host \
    -v /etc/hostname:/frp/username
    -e server_addr=10.10.10.10 \
    -e server_port=7000 \
    -e privilege_token=edt-1234 \
    -e remote_port=7001 \
    frpc
