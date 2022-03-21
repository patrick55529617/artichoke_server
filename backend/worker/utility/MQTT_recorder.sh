#!/usr/bin/env bash

# Usage:
# /home/edt/MQTT_recorder/main.sh <server ip> <artichoke-server client-id> <record file>
# eg: /home/edt/MQTT_recorder/main.sh 10.101.1.58

if [ -z "$1" ]
then
    echo "No MQTT IP"
    #echo $(date +"%FT%T"),,
    exit 0
else
    mqtt_server_ip=$1
fi

if [ -z "$2" ]
then
    artichoke_server="artichoke_postgresql_v1.7.4"
else
    artichoke_server=$2
fi

if [ -z "$3" ]
then
    record_file=/home/edt/MQTT_recorder/data.csv
else
    record_file=$3
fi


curl -s http://admin:public@$mqtt_server_ip:18083/api/v2/sessions/$artichoke_server | \
	jq --arg date $(date +"%FT%T") \
	   --arg server $mqtt_server_ip \
	   --arg receive $(curl -s http://admin:public@$mqtt_server_ip:18083/api/v2/monitoring/metrics | jq '.result[0] | .[]."messages/received"') \
	   -j '{a: $date}.a, ",", .result.objects[0].mqueue_len, ",", {a: $receive}.a,",", {a: $server}.a, "\n"' >> $record_file
