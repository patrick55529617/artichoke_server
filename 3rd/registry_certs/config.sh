#!/bin/sh

# Server config
SERVER_USER=  # add your server account.
SERVER_PORT=5000
SERVER_DOMAIN_URL=wifiprobe.edt.testritegroup.com
SERVER_URL=10.101.26.188
SERVER_CONF_FOLDER=/usr/local/src/registry
SERVER_IMAGE_VOLUMN=/var/local/registry/

# Client (for example: 10.3.0.100)
DEVICE_IP=10.3.0.100 

# Generate STL key and htpasswd password
KEY_FOLDER=keys
KEY_FILE=domain.key
CERT_FILE=domain.cert

# login user & password
DOCKER_LOGIN_FOLDER=auth 
DOCKER_LOGIN_USER=edt
DOCKER_LOGIN_PASSWORD= # you should know it. 
