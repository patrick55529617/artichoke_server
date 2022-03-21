#!/usr/bin/env bash

set -e
SERVER_REGISTRY=wifiprobe.edt.testritegroup.com:5000
IMAGE_NAME=emqttd

docker build -t ${SERVER_REGISTRY}/${IMAGE_NAME}:v2.3.4 .
