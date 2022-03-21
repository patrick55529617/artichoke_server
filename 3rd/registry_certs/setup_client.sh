#!/bin/sh

# load config variable
. config.sh

scp ${KEY_FOLDER}/${CERT_FILE} \
    edt@${DEVICE_IP}:/etc/docker/certs.d/${SERVER_DOMAIN_URL}:${SERVER_PORT}/ca.crt
