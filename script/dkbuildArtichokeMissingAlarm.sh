#!/usr/bin/env sh

tag=$1
if [ $# -ne 1 ]; then
    printf "Usage:\n sh $0 <version | tag>\n";
    exit
fi

domain="wifiprobe.edt.testritegroup.com:5000"
image_name="artichoke_missing_alarm"


echo "---Docker build latest artichoke_missing_alarm image (${tag})---"
docker build \
    -t ${domain}/${image_name}:${tag} \
    --file missing_alarm.dockerfile \
    .

echo "---Docker build complete---"

echo "----Upload artichoke_missing_alarm image to ${domain}/${image_name}:${tag}"
docker push ${domain}/${image_name}:${tag}
echo "---Docker push complete---"
