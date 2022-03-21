#!/bin/sh -e
if [ -n "$@" ]; then
  exec "$@"
fi

if [ -n "$bind_port" ]; then
  sed -i 's/bind_port = .*/bind_port = '"$bind_port"'/g' ./frps.ini
else
  echo "No bind_port"
  exit 1
fi

if [ -n "$dashboard_port" ]; then
  sed -i 's/dashboard_port = .*/dashboard_port = '"$dashboard_port"'/g' ./frps.ini
else
    echo "No dashboard_port"
    exit 1
fi

if [ -n "$dashboard_user" ]; then
  sed -i 's/dashboard_user = .*/dashboard_user = '"$dashboard_user"'/g' ./frps.ini
fi

if [ -n "$dashboard_pwd" ]; then
  sed -i 's/dashboard_pwd = .*/dashboard_pwd = '"$dashboard_pwd"'/g' ./frps.ini
fi

if [ -n "$privilege_allow_ports" ]; then
  sed -i 's/privilege_allow_ports = .*/privilege_allow_ports = '"$privilege_allow_ports"'/g' ./frps.ini
else
    echo "No privilege_allow_ports"
    exit 1
fi

if [ -n "$privilege_token" ]; then
  sed -i 's/privilege_token = .*/privilege_token = '"$privilege_token"'/g' ./frps.ini
else
  echo "No privilege_token"
  exit 1
fi

exec ./frps -c frps.ini

