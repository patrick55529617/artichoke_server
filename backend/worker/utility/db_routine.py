# -*- coding: utf-8 -*-
# !/usr/bin/env python3
import os
import logging.handlers
import pandas as pd
import bz2
import click
from sqlalchemy import create_engine
from datetime import date, timedelta, datetime
from configparser import ConfigParser

logger = logging.getLogger(__name__)


def rotator(source, dest):
    with open(source, 'rb') as f:
        with bz2.BZ2File(dest + '.bz2', 'w') as out:
            out.write(f.read())
    os.remove(source)


def logger_setting():
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)-15s %(levelname)s %(processName)s-%(threadName)s,%(module)s,%(funcName)s,ln %(lineno)d: %(message)s'
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

    if not os.path.exists('log'):
        os.makedirs('log')
    formatter = logging.Formatter(LOG_FORMAT)
    handler = logging.handlers.TimedRotatingFileHandler("log/refresh.log", when="midnight", backupCount=30)
    handler.setFormatter(formatter)
    handler.rotator = rotator
    logging.getLogger().addHandler(handler)


def db_url(config_path: str) -> str:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    db_url = config['DATABASE']['MASTER_URL']
    return db_url


def get_schema(config_path: str) -> str:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    schema = config['DB_ROUTINE']['schema']
    return schema


class DatabaseRoutine:
    def __init__(self, nday: int, target_date: str, site_id: str, channel: str, config_path: str):
        self._target_date = self._get_iso_date(target_date, nday)
        self._site_id = site_id
        self._channel = channel
        self._engine = create_engine(db_url(config_path))
        self._schema = get_schema(config_path)

    @staticmethod
    def _get_iso_date(target_date, nday: int) -> str:
        return (date.today() - timedelta(nday)).strftime("%Y-%m-%d") if not target_date else target_date

    def refresh_people_count(self):
        """Insert yesterday statistics into table people_count"""
        sql = f"""SET SESSION time zone 'Asia/Taipei';
                 INSERT INTO {self._schema}.people_count SELECT * FROM ( """
        is_weekend = True if (datetime.strptime(self._target_date, '%Y-%m-%d').isoweekday() >= 6) else False
        b_first = True
        for sid, site in self._read_released_site_info().iterrows():
            open_hour = site['open_hour_wend'] if is_weekend else site['open_hour']
            closed_hour = site['closed_hour_wend'] if is_weekend else site['closed_hour']
            if b_first:
                b_first = False
            else:
                sql += """UNION """
            # If the closing time is on the hour, closed_hour = closed_hour - 1 hour;
            # If the minute of the closing time is 30 minutes, closed_hour = closed_hour.
            if closed_hour.minute == 0:
                closed_hour = closed_hour.hour - 1
            elif closed_hour.minute == 30:
                closed_hour = closed_hour.hour
            sql += f"""SELECT '{sid}' as site_id, time, customers as count
                        FROM {site['func'][0]}('{self._target_date}', '{self._target_date}') WHERE date_part('hour', time)
                        BETWEEN {open_hour.hour} AND {closed_hour}
                    """
        sql += """) AS TAB ORDER by site_id, time ASC
               ON CONFLICT (site_id, time) DO UPDATE SET count=excluded.count;"""
        logger.info(sql)
        with self._engine.connect().execution_options(autocommit=True) as conn:
            conn.execute(sql)

    def _read_released_site_info(self) -> pd.DataFrame:
        sql = """SELECT * FROM site_info WHERE is_released """
        if self._channel:
            sql += f"""AND channel='{self._channel}' """
        if self._site_id:
            sql += f"""AND site_id='{self._site_id}' """
        data = pd.read_sql(sql=sql, con=self._engine).set_index('site_id')
        return data


if __name__ == '__main__':
    @click.command()
    @click.option('-n', '--nday', default=1, help='n days ago. Default is yesterday.')
    @click.option('-d', '--target_date', default=None, help='Target date with format YYYY-MM-DD. eg.2017-12-25')
    @click.option('-s', '--site_id', default=None, help='Site id. eg.1A01')
    @click.option('-t', '--channel', default=None, help='channel. eg.TLW')
    @click.option('-p', '--config_path', default='./config/artichoke_base_service.ini', help='config path')
    def main(nday=1, target_date=None, site_id=None, channel=None, config_path='./config/artichoke_base_service.ini'):
        try:
            db_routine = DatabaseRoutine(nday, target_date, site_id, channel, config_path)
            db_routine.refresh_people_count()
            logger.info('Done')
        except Exception as e:
            logger.exception(e)
            raise e

    main()
