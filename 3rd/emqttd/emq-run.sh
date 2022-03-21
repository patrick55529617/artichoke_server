#! /usr/bin/env bash

# Run docker command
docker run -d \
    --restart=always \
    --name emq-edt \
    -p 1883:1883 \
    -p 8083:8083 \
    -p 8883:8883 \
    -p 8084:8084 \
    -p 18083:18083 \
    -e EMQ_MQTT__MQUEUE__MAX_LENGTH=1000000 \
    -e EMQ_MQTT__CLIENT__ENABLE_STATS=on \
    -e EMQ_MQTT__SESSION__ENABLE_STATS=on \
    wifiprobe.edt.testritegroup.com:5000/emqttd:v2.3.4

