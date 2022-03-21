#!/usr/bin/env bash

tag=$1

# Delete old artichoke container
cid=$(docker ps -aqf "name=artichoke_missing_alarm")
echo "---Remove artichoke missing alarm---"
docker rm ${cid}

docker run -d \
    --net=host \
    --name artichoke_missing_alarm_${tag} \
    -v /home/edt/.ssh/id_rsa:/var/local/.ssh/id_rsa \
    -v /usr/local/src/artichoke_base_service.ini:/code/config/artichoke_base_service.ini \
    -v /usr/local/src/artichoke_rawdata_missing_alarm.py:/code/src/artichoke_rawdata_missing_alarm.py \
    -v /var/local/sharepoint:/var/local/sharepoint \
    wifiprobe.edt.testritegroup.com:5000/artichoke_missing_alarm:${tag}
