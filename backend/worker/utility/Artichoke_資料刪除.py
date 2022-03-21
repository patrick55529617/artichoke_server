#!/usr/bin/env python
# coding: utf-8

import os, sys
import pandas as pd
import time, pytz
import click
import bz2
import logging
import logging.handlers
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
import logging.config
import configparser


if __name__ == '__main__':
    @click.command()
    @click.option('--artichoke_base_service_config_file_path', default='./config/artichoke_base_service.ini', help='請填寫 artichoke_base_service.ini 檔案位置')
    @click.option('--backup_save_dir', default='/var/local/artichoke/db_backup/', help='請填寫要刪除的年月份資料之前備份的檔案路徑')
    @click.option('--year', help='請填寫要刪除的年份')
    @click.option('--month', help='請填寫要刪除的月份')
    
    def run(artichoke_base_service_config_file_path,
           backup_save_dir,
           year,
           month):
        
        ##################################################################
        # Config
        ##################################################################
        drop_month = {
            str(year):[month]
        }


        logger = logging.getLogger(__name__)

        LOGGING_CONFIG = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'simple': {
                    'format': "%(asctime)s:%(levelname)s:%(message)s",
                },
                'detailed': {
                    'format': '%(asctime)s %(module)-17s line:%(lineno)-4d %(levelname)-8s %(message)s',
                },
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                }
            },
            'root': {
                'handlers': ['console'],
                'level': 'INFO',
            }
        }
        logging.config.dictConfig(LOGGING_CONFIG)

        ##################################################################
        # Load and setup config
        ##################################################################
        
        if year is None:
            logger.info('請填寫要刪除的年月份，指令格式參考 : python3 ./Artichoke_資料刪除.py --year 2020(年份) --month 5(月份)')
            exit()
            
        if month is None:
            logger.info('請填寫要刪除的年月份，指令格式參考 : python3 ./Artichoke_資料刪除.py --year 2020(年份) --month 5(月份)')
            exit()

        logger.info('# Load config')
        logger.info('Work dir                                : {}'.format(os.getcwd()))
        logger.info('Load artichoke base service config path : {}'.format(artichoke_base_service_config_file_path))

        # base service config
        config = configparser.ConfigParser()
        config.read([artichoke_base_service_config_file_path])

        # util config
        logger.info('DB_URL_ADMIN                            : {}'.format(config['ARTICHOKE']['DB_URL_ADMIN']))
        logger.info('Backup save dir                         : {}'.format(backup_save_dir))
        logger.info('Drop year_month                         : {}_{}\n'.format(year,str(month).zfill(2)))

        db_url = config['ARTICHOKE']['DB_URL_ADMIN']
        engine = create_engine(db_url)

        ##################################################################
        # Define functions
        ##################################################################

        def humanbytes(B):
           'Return the given bytes as a human friendly KB, MB, GB, or TB string'
           B = float(B)
           KB = float(1024)
           MB = float(KB ** 2) # 1,048,576
           GB = float(KB ** 3) # 1,073,741,824
           TB = float(KB ** 4) # 1,099,511,627,776

           if B < KB:
              return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
           elif KB <= B < MB:
              return '{0:.2f} KB'.format(B/KB)
           elif MB <= B < GB:
              return '{0:.2f} MB'.format(B/MB)
           elif GB <= B < TB:
              return '{0:.2f} GB'.format(B/GB)
           elif TB <= B:
              return '{0:.2f} TB'.format(B/TB)

        ##################################################################
        # Droping rawdata ...
        ##################################################################

        # 清除資料

        logger.info("\n請再次確認，上述設定年月是否錯誤!")
        input('按下任意鍵，開始執行清除資料...')

        sql_truncate_template = """DROP TABLE {}"""

        sql_template = """
        SELECT *, pg_size_pretty(total_bytes) AS total
            , pg_size_pretty(index_bytes) AS INDEX
            , pg_size_pretty(toast_bytes) AS toast
            , pg_size_pretty(table_bytes) AS TABLE
        FROM (
            SELECT *, total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes FROM (
              SELECT c.oid,nspname AS table_schema, relname AS TABLE_NAME
                      , c.reltuples AS row_estimate
                      , pg_total_relation_size(c.oid) AS total_bytes
                      , pg_indexes_size(c.oid) AS index_bytes
                      , pg_total_relation_size(reltoastrelid) AS toast_bytes
              FROM pg_class c
              LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE relkind = 'r'
                  AND nspname = 'public'
                  AND relname LIKE '%%_{year}_{month}'
            ) a
        ) a
        """

        for year in drop_month:
            for month in drop_month[year]:
                sql = sql_template.format(year=year, month=str(month).zfill(2))
                tmp_df = pd.read_sql(sql,engine)
                usage_size = humanbytes(tmp_df['total_bytes'].sum())
                logger.info('查詢要 Drop 的表格 SQL :\n{}\n\n'.format(sql))
                logger.info('開始 Drop 表格...')

                for tbl_name in tmp_df['table_name']:        
                    month_str = str(month).zfill(2)
                    path = '{}/{}_{}/{}.bz2'.format(backup_save_dir,year,month_str,tbl_name)
                    sql = sql_truncate_template.format(tbl_name)

                    if os.path.exists(path):
                        engine.execute(sql)
                    else:
                        logger.warning("[Warning] 查無備份資料的表格 : {}".format(tbl_name))

        logger.info('Drop 表格執行完成!')

        
    run()

