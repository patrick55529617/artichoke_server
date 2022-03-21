#!/usr/bin/env sh

tag=$1
if [ $# -ne 1 ]; then
    printf "Usage:\n sh $0 <version | tag>\n";
    exit
fi

domain="wifiprobe.edt.testritegroup.com:5000"
image_name="artichoke_server"


echo "---Docker build latest artichoke_server image (${tag})---"
docker build \
    -t ${domain}/${image_name}:${tag} \
    -t ${domain}/${image_name}:latest \
    --file mqtt_sub.dockerfile \
    .
echo "---Docker build complete---"


echo "----Upload artichoke_server image to ${domain}/${image_name}:${tag}"
docker push ${domain}/${image_name}:${tag}
docker push ${domain}/${image_name}:latest
echo "---Docker push complete---"
