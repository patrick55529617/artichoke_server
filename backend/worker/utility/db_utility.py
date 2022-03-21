# -*- coding: utf-8 -*-
# !/usr/bin/env python3


import click
import numpy as np
import pandas as pd
import logging.handlers
from sqlalchemy import create_engine
from configparser import ConfigParser


LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)-15s %(levelname)s %(processName)s-%(threadName)s,%(module)s,%(funcName)s: %(message)s'
logger = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
formatter = logging.Formatter(LOG_FORMAT)
handler = logging.handlers.RotatingFileHandler('log/daily.log', maxBytes=1024 * 1024, backupCount=2)
handler.setFormatter(formatter)
logger.addHandler(handler)


def db_url(config_path: str) -> str:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    dburl = config['DATABASE']['MASTER_URL']
    return dburl


class DbUtility:
    def __init__(self, schema: str, file: str, config_path: str):
        self._schema = schema
        self._file = file
        self._engine = create_engine(db_url(config_path))

    def _register_site_from_file(self):
        df = pd.read_excel(self._file, header=0, index_col=1)
        for sid, info in df.iterrows():
            if sid is np.nan:
                logger.info('Empty row')
                break
            try:
                info['Sniffer MAC'] = info['Sniffer MAC'].lower()
                sql = f"""INSERT INTO {self._schema}.site_info (site_id, sname, channel, open_hour, closed_hour, open_hour_wend, closed_hour_wend, is_released, android_rate, wifi_rate, region, "group", alg_version) VALUES ('{sid}','{info['門店']}', '{info['Channel']}', '10:00:00+08:00', '21:00:00+08:00', '10:00:00+08:00', '21:00:00+08:00', 'false', '0.55', '0.66', '{info['region']}', '{info['group']}', '1')"""
                self._engine.execute(sql)
                logger.info(f"Site data insert into {self._schema}.site_info table")
                sql = f"""INSERT INTO {self._schema}.sniffer_info (site_id, sniffer_id, is_active, rssi) VALUES ('{sid}', '{info['Sniffer MAC']}', 'false', '-90')"""
                self._engine.execute(sql)
                logger.info(f"Sniffer data insert into {self._schema}.sniffer_info table")
            except Exception as e:
                logger.error(f'[ERROR]_register_site_from_file：{e}')
        logger.info("Register finish!!")

    def main_proc(self):
        self._register_site_from_file()


if __name__ == '__main__':
    @click.command()
    @click.option('--file', '-f', default=None, help='Site info excel file')
    @click.option('-p', '--config_path', default='./config/artichoke_base_service.ini', help='config path')
    def run(file=None, config_path='./config/artichoke_base_service.ini'):
        config = ConfigParser()
        config.read(config_path, encoding='UTF-8')
        schema = config['CREATE_DB_TABLE']['schema']
        db_utility = DbUtility(schema=schema, file=file, config_path=config_path)
        db_utility.main_proc()


    run()
