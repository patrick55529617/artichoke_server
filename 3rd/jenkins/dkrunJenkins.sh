#!/usr/bin/env sh

docker rm -f jenkins

docker run -d --name jenkins -p 9000:8080 \
-p 50000:50000 \
-v /usr/bin/jq:/usr/bin/jq \
-v /root/.docker/config.json:/.docker/config.json \
-v /usr/bin/sshpass:/usr/bin/sshpass \
-v /root/.ssh/iot_id_rsa:/id_rsa \ # artichoke client sshkey
-v /usr/local/src/jenkins/frpc.tar:/var/jenkins_home/frpc.tar \
-v /usr/local/src/jenkins/artichoke_base_service.ini:/var/jenkins_home/artichoke_base_service.ini \
-v /var/run/docker.sock:/var/run/docker.sock \
-v /var/jenkins_home:/var/jenkins_home \
wifiprobe.edt.testritegroup.com:5000/jenkins:v0.0.1
