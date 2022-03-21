docker run -d \
  --name graphite \
  --restart=always \
  -p 8080:80 \
  -p 2003-2004:2003-2004 \
  -p 2023-2024:2023-2024 \
  -p 8125:8125/udp \
  -p 8126:8126 \
  -v /var/local/graphite/storage:/opt/graphite/storage \
  -v /var/local/graphite/conf:/opt/graphite/conf \
  graphiteapp/graphite-statsd
  #-v /local/path/to/.htpasswd:/etc/nginx/.htpasswd
  #-v /path/to/storage-schemas.conf:/opt/graphite/conf/storage-schemas.conf \
