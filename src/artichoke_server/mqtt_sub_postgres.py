# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os
import os.path
import sys
import time
import json
import pytz
import logging
import logging.handlers
import psycopg2
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.sql import text
import sqlalchemy.exc
import paho.mqtt.client as mqtt
import click

logger = logging.getLogger(__name__)


def insert2imtest(engine, **data):
    try:
        engine.execute(
            text(
                """INSERT INTO
                "imtest".rawdata
                ("rt", "sa", "da", "rssi", "seqno", "cname",
                    "pkt_type", "pkt_subtype", "ssid", "channel",
                    "upload_time", "delivery_time", "sniffer")
                VALUES( 
                :rt, :sa, :da, :rssi, :seqno, :cname, :pkt_type, :pkt_subtype, :ssid, :channel,
                    :upload_time, :delivery_time, :sniffer)
                """
            ),
            **data
        )
    
    except sqlalchemy.exc.IntegrityError as e:
        if hasattr(e.orig, 'pgcode'):
            if e.orig.pgcode == '23505':
                logger.debug('duplicate key value violates unique constraint', exc_info=True)
                return
        logger.error(e, exc_info=True)
    except Exception as e:
        logger.error(e, exc_info=True)


def main(mqtt_server, mqtt_port, mqtt_topic, mqtt_client_id, mqtt_username, mqtt_password, db_url):
    """The MQTT Sub programe for PostgreSQL database. """
    logger.info('MQTT Server : %s, port: %s, topic: %s, username: %s',
                mqtt_server, mqtt_port, mqtt_topic, mqtt_username)

    engine = create_engine(db_url)
    logger.info('DB: %s', engine)

    # TODO: All devices at GMT+8
    tw = pytz.timezone('Asia/Taipei')

    def on_connect(client, userdata, flags, rc):
        if rc == mqtt.CONNACK_ACCEPTED:
            client.subscribe(mqtt_topic, qos=1)
        else:
            logger.error('MQTT failed connect and the rc code is %d.', rc)

    # The callback for when a PUBLISH message is received from the server.
    def on_message(client, userdata, msg):
        topic = msg.topic
        mqtt_msg = json.loads(msg.payload)

        antenna_mac = topic.split('/')[-1]
        data = dict()
        data.setdefault('ssid', '')
        data.setdefault('cname', '')
        data.setdefault('upload_time', None)
        data.setdefault('delivery_time', datetime.utcnow())
        data.setdefault('sniffer', antenna_mac)
        
        # set default as -1, 修正 raw data 沒有 subtype 時 insert 到 raw data table 發生 error 無法寫入, 先 workaround 讓資料寫入
        data.setdefault('pkt_subtype', -1) 

        transfer_key = {
            'rt': 'rt',
            'type': 'pkt_type',
            'subtype': 'pkt_subtype',
            'Channel': 'channel',
            'rssi': 'rssi',
            'ssid': 'ssid',
            'sa': 'sa',
            'da': 'da',
            'sn': 'seqno',
            'cname': 'cname',
            'upload_time': 'upload_time',
        }
        for old_k, new_k in transfer_key.items():
            if old_k in mqtt_msg:
                # remove colon sign
                if old_k in ['sa', 'da']:
                    data[new_k] = mqtt_msg[old_k].replace(':', '').lower()
                # Set Timezone string format
                elif old_k in ['rt', 'upload_time']:
                    data[new_k] = str(datetime.fromtimestamp(
                        mqtt_msg[old_k]).astimezone(tw))
                else:
                    data[new_k] = mqtt_msg[old_k]

        try:
            logger.debug(
                "Insert data into database. the data rt is %s and topic is %s.", data['rt'], topic)
            while True:
                try:
                    engine.execute(text(
                        """INSERT INTO
                        rawdata_{} 
                        ("rt", "sa", "da", "rssi", "seqno", "cname",
                            "pkt_type", "pkt_subtype", "ssid", "channel",
                            "upload_time", "delivery_time", "sniffer")
                        VALUES( 
                        :rt, :sa, :da, :rssi, :seqno, :cname, :pkt_type, :pkt_subtype, :ssid, :channel,
                            :upload_time, :delivery_time, :sniffer)
                        """.format(antenna_mac)),
                        **data)
                except sqlalchemy.exc.OperationalError as e:
                    logger.exception(e)
                    time.sleep(5)
                else:
                    break

        except sqlalchemy.exc.IntegrityError as e:
            if hasattr(e.orig, 'pgcode'):
                if e.orig.pgcode == '23505':
                    logger.debug(
                        'duplicate key value violates unique constraint', exc_info=True)
                    return
                elif e.orig.pgcode == '23514':
                    logger.warning(
                        '''The rawdata_"%s" of partition key of the failing row contains. Inserting to "imtest".rawdata.''', antenna_mac)
                    insert2imtest(engine, sniffer_mac=antenna_mac, **data)
                    return
                else:
                    logger.warning('SQL error: {}, {}'.format(
                        e.orig.pgcode, e.orig.pgerror))
            logger.exception(e)
        except sqlalchemy.exc.ProgrammingError as e:
            if hasattr(e.orig, 'pgcode'):
                pgcode = e.orig.pgcode
                if pgcode == '42P01':
                    logger.warning(
                        'The rawdata_"%s" is not found. Inserting to "imtest".rawdata.', antenna_mac)
                    insert2imtest(engine, sniffer_mac=antenna_mac, **data)
                    return

            logger.exception(e)
        except ValueError as e:
            logger.debug('A string literal cannot contain NUL.')
        except Exception as e:
            logger.exception(e)

    def on_log(client, userdata, level, buf):
        send_or_receive, mqtt_type, *msg = buf.split(' ', 3)
        if mqtt_type in ('PUBLISH', 'PUBACK'):
            logger.debug(buf)
        else:
            logger.info(buf)

    if mqtt_client_id:
        client = mqtt.Client(client_id=mqtt_client_id, clean_session=False)
    else:
        client = mqtt.Client()
    
    if mqtt_username and mqtt_password:
        client.username_pw_set(mqtt_username, mqtt_password)
    
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_log = on_log
    client.connect_async(mqtt_server, mqtt_port)
    client.loop_forever(retry_first_connection=True)


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())


if __name__ == '__main__':
    LOG_FORMAT = '%(asctime)-15s %(levelname)s %(processName)s-%(threadName)s-%(funcName)s, line %(lineno)d:%(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT)

    @click.command()
    @click.option('--mqtt_server', default='10.101.26.187', envvar='mqtt_server', help='The MQTT Server.')
    @click.option('--mqtt_port', default=1883, envvar='mqtt_port', help='The MQTT port.')
    @click.option('--mqtt_topic', default='artichoke/#', envvar='mqtt_topic', help='The MQTT topic.')
    @click.option('--mqtt_username', default=None, envvar='mqtt_username', help='The MQTT username.')
    @click.option('--mqtt_password', default=None, envvar='mqtt_password', help='The MQTT password.')
    @click.option('--mqtt_client_id', default=None, envvar='mqtt_client_id', help='The MQTT Subscribe id.')
    @click.option('--db_url', envvar='db_url',
                  help='The PostgreSQL Server URL. (ex: postgresql+psycopg2://scott:tiger@localhost/mydatabase)')
    @click.option('--sentry_key', envvar='sentry_key', help='Sentry service key.')
    @click.option('--mail_server', envvar='mail_server', help='Alert Mail Server.')
    @click.option('--mail_from', envvar='mail_from', help='Alert mail from mail addree.')
    @click.option('--to_mail', envvar='to_mail', help='Alert to mail addree (commna).')
    def run(sentry_key, mail_server, mail_from, to_mail, *args, **kwargs):
        if os.environ.get('ENV', '') == 'production':
            stdout_logger = logging.getLogger('STDOUT')
            sl = StreamToLogger(stdout_logger, logging.INFO)
            sys.stdout = sl

            stderr_logger = logging.getLogger('STDERR')
            sl = StreamToLogger(stderr_logger, logging.ERROR)
            sys.stderr = sl

            if sentry_key:
                logger.info('Enable Sentry logging service.')
                # Sentry configuration
                from raven import Client
                from raven.handlers.logging import SentryHandler
                client = Client(sentry_key)
                handler = SentryHandler(client)
                handler.setLevel(logging.WARNING)

            if not os.path.exists('log'):
                os.makedirs('log')
            formatter = logging.Formatter(LOG_FORMAT)
            handler = logging.handlers.TimedRotatingFileHandler(
                "log/app", when="midnight", backupCount=30)
            handler.setFormatter(formatter)
            logging.getLogger().addHandler(handler)

            if mail_server and mail_from and to_mail:
                logger.info(
                    'Enable mail logging service (Mail server:%s).', mail_server)
                toaddrs = to_mail.split(',')
                subject = '[{}] Artichoke Server Error'.format(os.uname()[1])
                handler = logging.handlers.SMTPHandler(
                    mail_server, mail_from, toaddrs, subject)
                handler.setLevel(logging.WARNING)
                handler.setFormatter(formatter)
                logging.getLogger().addHandler(handler)
        main(*args, **kwargs)

    run()
