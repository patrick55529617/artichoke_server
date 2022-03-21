#!/bin/sh
. config.sh

mkdir -p ${KEY_FOLDER}
mkdir -p ${DOCKER_LOGIN_FOLDER}

docker run \
  --entrypoint htpasswd \
  registry:2 \
  -Bbn ${DOCKER_LOGIN_USER} ${DOCKER_LOGIN_PASSWORD} > ${DOCKER_LOGIN_FOLDER}/htpasswd

# generate key
openssl req -newkey rsa:4096 -nodes -sha256 \
    -keyout ${KEY_FOLDER}/${KEY_FILE} -x509 -days 3560 \
    -out ${KEY_FOLDER}/${CERT_FILE} -subj "/CN=${SERVER_DOMAIN_URL}"
