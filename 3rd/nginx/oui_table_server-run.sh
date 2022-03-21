docker run \
  -d \
  --restart=always \
  --name=oui_server \
  -p 8080:80 \
  -v /usr/local/src/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx
