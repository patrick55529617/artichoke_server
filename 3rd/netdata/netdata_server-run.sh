docker run \
  -d \
  --cap-add SYS_PTRACE \
  --restart=always \
  --name netdata_server \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v $PWD/config/netdata_server.conf:/etc/netdata/netdata.conf \
  -v $PWD/config/stream_server.conf:/etc/netdata/stream.conf \
  -v $PWD/config/netdata-memory.conf:/etc/sysctl.d/netdata-memory.conf \
  -p 19999:19999 \
  --net=host \
  firehol/netdata
