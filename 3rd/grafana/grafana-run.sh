docker run -d \
  --name grafana \
  --restart=always \
  -p 3000:3000 \
  -v /var/local/grafana/etc:/etc/grafana \
  -v /var/local/grafana/var/lib:/var/lib/grafana \
  -v /var/local/grafana/var/log:/var/log/grafana \
  grafana/grafana
