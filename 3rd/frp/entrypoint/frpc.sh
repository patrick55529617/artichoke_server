#!/bin/sh -e
if [ -n "$@" ]; then
  exec "$@"
fi

if [ -n "$server_addr" ]; then
  sed -i 's/server_addr = .*/server_addr = '"$server_addr"'/g' ./frpc.ini
else
  echo "No server_addr"
  exit 1
fi

if [ -n "$server_port" ]; then
  sed -i 's/server_port = .*/server_port = '"$server_port"'/g' ./frpc.ini
else
  echo "No server_port"
  exit 1
fi

if [ -n "$user" ]; then
  sed -i 's/user = .*/user = '"$user"'/g' ./frpc.ini
else
  sed -i 's/user = .*/user = '$(head -1 ./username)'/g' ./frpc.ini
fi

if [ -n "$privilege_token" ]; then
  sed -i 's/privilege_token = .*/privilege_token = '"$privilege_token"'/g' ./frpc.ini
else
  echo "No privilege_token"
  exit 1
fi

if [ -n "$remote_port" ]; then
  sed -i 's/remote_port = .*/remote_port = '"$remote_port"'/g' ./frpc.ini
else
  echo "Remote port assigns by server"
fi

exec ./frpc -c frpc.ini
