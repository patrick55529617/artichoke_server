#!/usr/bin/env bash

tag=$1
db_url=$2

# Delete old artichoke container
cid=$(docker ps -aqf "name=artichoke_worker")
echo "---Remove artichoke worker---"
docker rm ${cid}

docker run -d \
    --net=host \
    --name artichoke_worker_${tag} \
    -e db_url=${db_url} \
    -e TZ=Asia/Taipei \
    -v /Users/mac/testrite/artichoke_server/backend/worker/main.py:/worker/main.py \
    wifiprobe.edt.testritegroup.com:5000/artichoke_worker:${tag}
