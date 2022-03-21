#!/usr/bin/env sh

tag=$(git describe --tags --abbrev=0)

domain="wifiprobe.edt.testritegroup.com:5000"
image_name="artichoke_worker"


echo "---Docker build latest artichoke_worker image (${tag})---"
docker build \
    -t ${domain}/${image_name}:${tag} \
    -t ${domain}/${image_name}:latest \
    --file worker.dockerfile \
    .

echo "---Docker build complete---"

echo "----Upload artichoke_worker image to ${domain}/${image_name}:${tag}"
docker push ${domain}/${image_name}:${tag}
docker push ${domain}/${image_name}:latest
echo "---Docker push complete---"
