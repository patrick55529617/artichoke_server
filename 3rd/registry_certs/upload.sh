#!/bin/sh
. config.sh

# Upload key
scp -r ${KEY_FOLDER} ${SERVER_USER}@${SERVER_URL}:${SERVER_CONF_FOLDER}

scp -r ${DOCKER_LOGIN_FOLDER} ${SERVER_USER}@${SERVER_URL}:${SERVER_CONF_FOLDER}
