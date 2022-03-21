# -*- coding: utf-8 -*-

"""
Monitor Main Function

History:
2021/10/05 Created by Patrick
"""

import requests
import smtplib
from sqlalchemy import create_engine
from configparser import ConfigParser
from email.header import Header
from email.mime.text import MIMEText
import logging
logger = logging.getLogger()


class Monitor:

    def __init__(self, config_path: str = '/monitor/artichoke_base_service.ini'):
        self._get_params(config_path)

    def _get_params(self, config_path: str):
        config = ConfigParser()
        config.read(config_path, encoding='UTF-8')

        # Mail Server & Sender
        self._mail_server = 'rs1.testritegroup.com'
        self._mail_sender = config['MAIL_SENDER']['artichoke']

        # Recipients
        self._recipients = config['RECIPIENTS']['alert_report']

        # Database config
        self._master_engine = create_engine(config['DATABASE']['MASTER_URL'])
        self._slave_engine = create_engine(config['DATABASE']['SLAVE_URL'])

        # API Server config
        self._api_server_url = 'http://10.101.2.108:8000/api/v1/util/health'

        # Catnip Shiny config
        self._catnip_channels = ["TLW", "HOLA", "HOI", "CB"]
        self._catnip_urls = [
            "http://dashboard.edt.testritegroup.com:8080/22081978/",
            "http://dashboard.edt.testritegroup.com:8080/11251977/",
            "http://hoi.edt.testritegroup.com/",
            "http://dashboard.edt.testritegroup.com:8080/16111989/",
        ]

        # MQTT Broker config
        self._mqtt_brokers = config['MQTT']['BROKERS']
        self._mqtt_api_token = config['MQTT']['API_TOKEN']

    def monitor_main_function(self):
        logger.info("Start monitoring modules.")
        self._check_api_server_status()
        self._check_mqtt_status()
        self._check_catnip_shiny_status()
        self._check_database_status()

    def _api_type_health_check(self, req_url: str, svc_name: str, header: dict = None) -> bool:
        resp = requests.get(req_url, headers=header)
        if resp.status_code == 200:
            logger.error(f"Service: {svc_name} with status_code: {resp.status_code}")
            logger.error(f"Content: {resp.text}")
            self._send_mail(svc_name)

    def _check_api_server_status(self):
        logger.info("Start check api server status.")
        self._api_type_health_check(
            self._api_server_url,
            "API Server",
            {"token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYXJ0aWNob2tlIiwiZXhwIjoxOTQ4OTQ1MjQwfQ.6PA1giAgumRy-Pao5Dgr7pAn2baVc2BSG2InwU2Sfjo"}
        )
        logger.info("Check api server status done.")

    def _check_mqtt_status(self):
        logger.info("Start check mqtt status.")
        for url in self._mqtt_brokers.split(","):
            self._api_type_health_check(url, f"MQTT Broker {url}", {"token": self._mqtt_api_token})
        logger.info("Check mqtt status done.")

    def _check_catnip_shiny_status(self):
        logger.info("Start check catnip shiny status.")
        for channel, url in zip(self._catnip_channels, self._catnip_urls):
            self._api_type_health_check(url, f"Catnip shiny {channel}")
        logger.info("Check catnip shiny status done.")

    def _check_database_status(self):
        logger.info("Start check database status.")
        try:
            self._master_engine.execute("SELECT 1")
        except Exception:
            self._send_mail("Master Database")
        try:
            self._slave_engine.execute("SELECT 1")
        except Exception:
            self._send_mail("Slave Database")
        logger.info("Check database status done.")

    def _send_mail(self, svc_name: str):
        """
        Send email using input dataframe.
        """
        title = f"""[Artichoke] Service: {svc_name} not working."""
        content = f"Service: {svc_name} health check fail, please check the service status."
        message = MIMEText(content, 'html', 'utf-8')
        message['Subject'] = Header(title, 'utf-8')
        message['To'] = self._recipients

        try:
            smtpObj = smtplib.SMTP(self._mail_server)
            logger.info(f"message to : {self._recipients}")
            smtpObj.sendmail(self._mail_sender, list(self._recipients.split(",")), message.as_string())
            logger.info("Successfully sent email")
        except smtplib.SMTPException:
            logger.info("Error: unable to send email", exc_info=True)


def setup_logger(logger):
    """Logger format setting"""
    LOG_MSG_FORMAT = "[%(asctime)s][%(levelname)s] %(module)s %(funcName)s(): %(message)s"
    LOG_FILENAME = "monitor.log"
    LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=logging.INFO, format=LOG_MSG_FORMAT, datefmt=LOG_TIME_FORMAT, filename=LOG_FILENAME)


if __name__ == '__main__':
    Monitor().monitor_main_function()
