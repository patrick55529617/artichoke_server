docker run -d --restart=always --name postgres \
  -v /var/local/postgresql/data:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=atk-1234 \
  --net=host \
  -p 5432:5432 \
  postgres
