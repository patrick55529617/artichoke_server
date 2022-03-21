#!/bin/sh
. config.sh

# Start registry service
docker run \
  -d \
  --restart=always \
  --name registry \
  -v ${SERVER_CONF_FOLDER}/${DOCKER_LOGIN_FOLDER}:/auth \
  -e "REGISTRY_AUTH=htpasswd" \
  -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm" \
  -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd \
  -v ${SERVER_CONF_FOLDER}/${KEY_FOLDER}:/certs \
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.cert \
  -e REGISTRY_HTTP_TLS_KEY=/certs/domain.key \
  -v ${SERVER_IMAGE_VOLUMN}:/var/lib/registry \
  -p 5000:5000 \
  registry:2
