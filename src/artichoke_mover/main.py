#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import paho.mqtt.subscribe as subscribe
import time

import click
import paho.mqtt.client as mqtt

__version__ = 'v1.1.0'

logger = logging.getLogger(__name__)


def publisher(to_mqtt, client_name):
    client_publisher = mqtt.Client(client_name)
    client_publisher.connect_async(to_mqtt)
    return client_publisher


def subscriber(mqtt_from, client_name):
    client_sub = mqtt.Client(client_name)
    client_sub.connect_async(mqtt_from)
    return client_sub


def main(mqtt_from, to_mqtt, mqtt_topic, client_name=None):
    client_name = client_name or f'artichoke_mover_{__version__}'

    logger.info(f'Mover task from {mqtt_from}-[{mqtt_topic}] to {to_mqtt}.')
    client_publisher = publisher(to_mqtt, client_name)
    client_subscriber = subscriber(mqtt_from, client_name)

    # The callback for when a PUBLISH message is received from the server.
    def on_message_wifi_packets_sub(client, userdata, msg):
        topic = msg.topic
        data = msg.payload
        client_publisher.publish(topic, data, qos=1)

    def on_connect(client, userdata, flags, rc):
        if rc == mqtt.CONNACK_ACCEPTED:
            logger.info(
                f'The subscriber connected with mqtt server {mqtt_from}')
            client_subscriber.subscribe(mqtt_topic, qos=1)
            client_subscriber.message_callback_add(
                mqtt_topic, on_message_wifi_packets_sub)

    client_publisher.loop_start()
    client_subscriber.on_connect = on_connect
    client_subscriber.loop_start()

    while True:
        time.sleep(3600)


if __name__ == '__main__':
    LOG_FORMAT = '%(asctime)-15s %(levelname)s %(processName)s-%(threadName)s-%(funcName)s, line %(lineno)d:%(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT)

    @click.command()
    @click.option('-from', '--mqtt_from', envvar='mqtt_from', help='A MQTT server url which data source server.')
    @click.option('-to', '--to_mqtt', envvar='to_mqtt', help='A MQTT server url which destination server.')
    @click.option('-name', '--client_name', envvar='client_name', help='The MQTT client id.')
    @click.option('--mqtt_topic', default='artichoke/#', envvar='mqtt_topic', help='These MQTT topic(s) be listened to cloning data.')
    def run(*args, **kwargs):
        main(*args, **kwargs)

    run()
