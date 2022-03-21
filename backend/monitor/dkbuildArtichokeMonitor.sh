#!/usr/bin/env sh

tag=$(git describe --tags --abbrev=0)

domain="wifiprobe.edt.testritegroup.com:5000"
image_name="artichoke_monitor"


echo "---Docker build latest artichoke_monitor image (${tag})---"
docker build \
    -t ${domain}/${image_name}:${tag} \
    -t ${domain}/${image_name}:latest \
    --file monitor.dockerfile \
    .

echo "---Docker build complete---"

echo "----Upload artichoke_monitor image to ${domain}/${image_name}:${tag}"
docker push ${domain}/${image_name}:${tag}
docker push ${domain}/${image_name}:latest
echo "---Docker push complete---"
