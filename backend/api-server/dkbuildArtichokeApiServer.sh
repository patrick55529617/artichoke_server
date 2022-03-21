#!/usr/bin/env sh

tag=$(git describe --tags --abbrev=0)

domain="wifiprobe.edt.testritegroup.com:5000"
image_name="artichoke_api-server"


echo "---Docker build latest artichoke_api-server image (${tag})---"
docker build \
    --build-arg version=${tag} \
    -t ${domain}/${image_name}:${tag} \
    -t ${domain}/${image_name}:latest \
    --file api-server.dockerfile \
    .

echo "---Docker build complete---"

echo "----Upload artichoke_api-server image to ${domain}/${image_name}:${tag}"
docker push ${domain}/${image_name}:${tag}
docker push ${domain}/${image_name}:latest
echo "---Docker push complete---"
