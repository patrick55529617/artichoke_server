#!/usr/bin/env python
# coding: utf-8

import os
import os.path
import glob
import logging
import pandas as pd
from shutil import copyfile
from sqlalchemy import create_engine
import click
from datetime import datetime
import os, sys
import pandas as pd
import time, pytz
import click
import bz2
import logging
import logging.handlers
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
import configparser
import logging.config
import pytz

if __name__ == '__main__':
    @click.command()
    @click.option('--artichoke_base_service_config_file_path', default='./config/artichoke_base_service.ini', help='請填寫 artichoke_base_service.ini 檔案位置')
    @click.option('--backup_save_dir', default='./', help='請填寫要刪除的年月份資料之前備份的檔案路徑')
    @click.option('--old_sniffer', default=None, help='請填寫舊 sniffer 天線的 MAC')
    @click.option('--new_sniffer', default=None, help='請填寫新 sniffer 天線的 MAC')
    @click.option('--new_sniffer_rawdata_drop_date', default=None, help='請填寫新 sniffer 天線 rawdata 要 drop 到哪天前(不含當天)，格式 : 2020-01-01')

    def run(artichoke_base_service_config_file_path,
           backup_save_dir,
           old_sniffer,
           new_sniffer,
           new_sniffer_rawdata_drop_date):
        
        ##################################################################
        # Config
        ##################################################################
        
        dt = datetime.now()
        tw = pytz.timezone('Asia/Taipei')
        twdt = tw.localize(dt)
        current_year = int(twdt.strftime('%Y'))
        check_years = list(range(2018,current_year+1))

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
        
        logger.info('# Load config')
        logger.info('Work dir                                : {}'.format(os.getcwd()))
        logger.info('Load artichoke base service config path : {}'.format(artichoke_base_service_config_file_path))

        # base service config
        config = configparser.ConfigParser()
        config.read([artichoke_base_service_config_file_path])

        db_backup_host = config['ARTICHOKE']['DB_BACKUP_HOST']
        db_backup_dir = config['ARTICHOKE']['DB_BACKUP_DIR']
        db_url = config['ARTICHOKE']['DB_URL_ADMIN']

        # util config
        logger.info('DB_URL_ADMIN                            : {}'.format(config['ARTICHOKE']['DB_URL_ADMIN']))
        logger.info('backup save dir                         : {}'.format(backup_save_dir))
        logger.info('backup rawdata check years              : {}'.format(check_years))
        logger.info('舊天線 sniffer mac                      : {}'.format(old_sniffer))
        logger.info('新天線 sniffer mac                      : {}'.format(new_sniffer))
        logger.info('新天線 rawdata 刪除資料到(不含該天)     : {}'.format(new_sniffer_rawdata_drop_date))
        
        input('\n請確認刪除資料日期正確，以及新舊天線 sniffer mac 正確，點擊任意鍵繼續...')

        engine = create_engine(db_url)
        
        ##################################################################
        # function define
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
        # 檢查刪除 new sniffer 資料 SQL
        ##################################################################

        logger.info(f"## 準備刪除 new sniffer {new_sniffer} rawdata {new_sniffer_rawdata_drop_date} 前的資料....\n")
        del_sql = f"""
        SET SESSION TIME ZONE 'Asia/Taipei';

        DELETE 
        FROM rawdata_{new_sniffer}
        WHERE rt < '{new_sniffer_rawdata_drop_date}'
        ;

        COMMIT;
        """

        logger.info(f"刪除 new sniffer rawdata SQL : \n{del_sql}")
        input('請確認 SQL 刪除的表格與時間正確，點擊任意鍵繼續...')

        ##################################################################
        # 執行刪除 new sniffer 資料 SQL
        ##################################################################

        logger.info(f"## 刪除 new sniffer {new_sniffer} rawdata {new_sniffer_rawdata_drop_date} 前的資料....\n")

        logger.info(f"執行 SQL :\n{del_sql}")
        engine.execute(del_sql)
        logger.info(f"刪除完成!")

        ##################################################################
        # 檢查 new sniffer 資料狀況
        ##################################################################

        logger.info(f"\n## 查詢 new sniffer 目前資料狀況")
        sql = f"""
        SET SESSION TIME ZONE 'Asia/Taipei';

        WITH first_rawdata AS (
            SELECT '最早資料' AS type, *
            FROM rawdata_{new_sniffer}
            ORDER BY rt ASC
            LIMIT 1
        )
        , last_rawdata AS (
            SELECT '最晚資料' AS type, *
            FROM rawdata_{new_sniffer}
            ORDER BY rt DESC
            LIMIT 1
        )

        SELECT *
        FROM first_rawdata
        UNION
        SELECT *
        FROM last_rawdata

        """
        tmp_df = pd.read_sql(sql,engine)
        logger.info(tmp_df)

        input(f'請確認新天線 {new_sniffer} {new_sniffer_rawdata_drop_date} 前的資料，都有刪除成功，點擊任意鍵繼續...')

        ##################################################################
        # 搬動 old sniffer 到 new sniffer
        ##################################################################

        logger.info(f"\n## 搬動資料舊天線 {old_sniffer} rawdata {new_sniffer_rawdata_drop_date} 前的資料到新天線 {new_sniffer}...")

        sql = f"""
        SET SESSION TIME ZONE 'Asia/Taipei';

        INSERT INTO rawdata_{new_sniffer}
            SELECT rt, sa, da, rssi, seqno, cname, pkt_type, pkt_subtype, ssid, channel, upload_time, delivery_time, '{new_sniffer}' AS sniffer
            FROM rawdata_{old_sniffer}
            WHERE rt < '{new_sniffer_rawdata_drop_date}'
        ;

        COMMIT;
        """

        logger.info(f'執行 SQL :\n{sql}')
        engine.execute(sql)

        logger.info("\n搬動資料 rawdata 完成!")

        ##################################################################
        # 查詢目前 new sniffer 資料狀況
        ##################################################################

        logger.info(f"\n## 查詢 new sniffer 目前資料狀況")
        sql = f"""
        SET SESSION TIME ZONE 'Asia/Taipei';

        WITH first_rawdata AS (
            SELECT '最早資料' AS type, *
            FROM rawdata_{new_sniffer}
            ORDER BY rt ASC
            LIMIT 1
        )
        , last_rawdata AS (
            SELECT '最晚資料' AS type, *
            FROM rawdata_{new_sniffer}
            ORDER BY rt DESC
            LIMIT 1
        )

        SELECT *
        FROM first_rawdata
        UNION
        SELECT *
        FROM last_rawdata

        """
        tmp_df = pd.read_sql(sql,engine)
        logger.info(tmp_df)

        input(f'請確認新天線 {new_sniffer} {new_sniffer_rawdata_drop_date} 前的資料，都有搬動成功，點擊任意鍵繼續...')

        ##################################################################
        # 複製 old sniffer 資料到 new sniffer 資料 (注意年份需指定)
        ##################################################################

        years = check_years

        files = []
        # r=root, d=directories, f = files
        for r, d, f in os.walk(backup_save_dir):
            for file in f:
                if ('.bz2' in file) and old_sniffer in file:
                    files.append(os.path.join(r, file))
        files.sort()

        logger.info('## 掃描備份資料需要轉移的檔案清單...')
        for file in files:
            logger.info(file) 

        logger.info('\n開始拷貝...')
        new_backup_file_list = []
        for year in years:
            for f in files:
                if old_sniffer in f:
                    if str(year) in f:
                        from_path = f
                        to_path = f.replace(old_sniffer,new_sniffer)
                        new_backup_file_list.append(to_path)

                        logger.info("> Copy from {}".format(from_path))
                        logger.info("       to   {}\n".format(to_path))
                        copyfile(from_path,to_path)
        logger.info('\n結束拷貝')

        logger.info('\n天線轉移完成!\n\n')

        ##################################################################
        # 產生 copy 檔案到備份機器之輩份目錄的 script
        # 請產生後依據說明執行 script
        ##################################################################

        cmd_template = """
        rsync -azv -e 'ssh -o "ProxyCommand ssh 工號@10.101.26.49 nc -w 1 %h 22"' {file_list}  工號@10.101.2.18:/tmp/artichoke_db_backup
        """

        print("""# 請接著依序執行以下步驟:""")

        print("""

        ## Step1. 請複製指令並在自己電腦的 Ternimal 上，貼上後執行
        """)
        file_list_str = ' '.join(new_backup_file_list)
        print(cmd_template.format(file_list=file_list_str))

        print(f"""
        ## Step2. 請複製指令並在主機 ({db_backup_host}) 的 Ternimal 上，貼上後執行
        """)
        file_list_str = ''
        for backup_file in new_backup_file_list:
            file_list_str += 'mv /tmp/artichoke_db_backup/'
            file_list_str += backup_file.split('/')[-1]
            file_list_str += ' '
            year_month_folder = backup_file.split('_')[-2] + '_' + backup_file.split('_')[-1].split('.')[0]
            file_list_str += f'{db_backup_dir}{year_month_folder}'
            file_list_str += ';\n'
        print(f"{file_list_str}")
            

    run()



