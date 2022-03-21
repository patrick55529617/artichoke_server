#!/bin/sh
. config.sh

# Start browser fronted
docker run \
  -d \
  --restart=always \
  --net=host  \
  --privileged  \
  -e ENV_DOCKER_REGISTRY_HOST=wifiprobe.edt.testritegroup.com  \
  -e ENV_DOCKER_REGISTRY_PORT=${SERVER_PORT}  \
  -e ENV_DOCKER_REGISTRY_USE_SSL=1  \
  -p 80:80 \
  konradkleine/docker-registry-frontend:v2

