docker run -d --restart=always --name netdata_client \
  --cap-add SYS_PTRACE \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v $PWD/config/netdata.conf:/etc/netdata/netdata.conf \
  -v $PWD/config/stream.conf:/etc/netdata/stream.conf \
  -p 19999:19999 \
  --uts=host \
  firehol/netdata
#  -h netdata_client_test \