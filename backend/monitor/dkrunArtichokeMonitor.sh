#!/usr/bin/env bash

tag=v2.10.0

docker run -d \
    --restart=always \
    --name artichoke_monitor_${tag} \
    -e TZ=Asia/Taipei \
    wifiprobe.edt.testritegroup.com:5000/artichoke_monitor:${tag}
