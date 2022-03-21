#!/usr/bin/env bash

tag=$1
specified_month=$2
db_url=$3

# Delete old artichoke container
cid=$(docker ps -aqf "name=artichoke_db_backup")
echo "---Remove artichoke db_backup---"
docker rm ${cid}

docker run -d \
    --net=host \
    --name artichoke_db_backup_${tag} \
    -v /var/local/db_backup/artichoke:/var/local/db_backup \
    -e specified_month=${specified_month} \
    -e db_url=${db_url} \
    wifiprobe.edt.testritegroup.com:5000/artichoke_db_backup:${tag}
