#!/usr/bin/env sh

tag=v0.0.1

domain="wifiprobe.edt.testritegroup.com:5000"
image_name="jenkins"


echo "---Docker build latest jenkins image (${tag})---"
docker build -t ${domain}/${image_name}:${tag} .

echo "---Docker build complete---"
# docker push ${domain}/${image_name}:${tag}
# echo "---Docker push complete---"
