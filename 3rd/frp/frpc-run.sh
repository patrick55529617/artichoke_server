docker run \
    -d \
    --name frps \
    --restart=always \
    -e bind_port=7000 \
    -e dashboard_port=7500 \
    -e privilege_token=edt-12345678091234567890123456 \
    -e privilege_allow_ports=7001-7499 \
    -p 7000-7500:7000-7500 \
    frps:v0.16.0
