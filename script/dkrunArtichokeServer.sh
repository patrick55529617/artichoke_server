#!/usr/bin/env bash

tag=$1
if [ $# -ne 1 ]; then
    printf "Usage:\n sh $0 <version | tag>\n";
    exit
fi

# Delete old artichoke container
cid=$(docker ps -aqf "name=artichoke-server")
echo "---Stop artichoke server---"
docker stop ${cid}

docker run -d \
    --restart=always \
    --net=host \
    --name artichoke-server_${tag} \
    -v /var/local/artichoke/log:/code/log \
    -e ENV=production \
    -e mqtt_topic=artichoke/# \
    -e mqtt_client_id=artichoke_postgresql_${tag} \
    -e mqtt_server=localhost \
    -e db_url=postgresql+psycopg2://artichoke:edt-1234@db.wifiprobe.edt.testritegroup.com/artichoke \
    wifiprobe.edt.testritegroup.com:5000/artichoke_server:${tag}

echo "---Delete old container ${cid}---"
docker rm ${cid}
