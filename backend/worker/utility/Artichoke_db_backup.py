#!/usr/bin/env python
# coding: utf-8

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import click
import configparser
import psycopg2
import bz2
import logging.config
import re
from typing import Union
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


def create_db_obj(db_url: str):
    engine = create_engine(db_url)
    make_session = sessionmaker(autocommit=False, autoflush=True, bind=engine)
    db = make_session()
    return engine, db


def check_backup_dir_exists(backup_save_dir: str, year: int, month: int) -> bool:
    """
    Check if db_backup saved folder exists, if not, help to create.
    """
    if not os.path.isdir(backup_save_dir):
        logger.warning(f"Directory {backup_save_dir} not created, script help to create.")
        os.mkdir(backup_save_dir)
    else:
        if os.path.isdir(backup_save_dir + '/{}_{:02d}'.format(year, month)):
            logger.warning(f"Month {year}/{month} is already backup")
            return True
    os.mkdir(backup_save_dir + '/{}_{:02d}'.format(year, month))
    return False


def get_specified_year_month(year, month):
    """
    Get year and month from environment setting (docker) or from config.
    """
    if year is None or month is None:
        specified_month = os.environ.get('specified_month')
        if specified_month:
            year, month = specified_month.split('/')
        else:
            logger.info('請填寫要備份的年月份，指令格式參考 : python3 Artichoke_db_backup.py --year 2020(年份) --month 5(月份)')
            exit()
    return int(year), int(month)


def get_db_url(artichoke_base_service_config_file_path: str) -> str:
    """
    Get Database Url from environment setting (docker) or from local.
    """
    config = configparser.ConfigParser()
    config.read([artichoke_base_service_config_file_path])
    db_url = config['DATABASE']['MASTER_URL']
    return db_url


def show_config_in_screen(
    artichoke_base_service_config_file_path: str,
    backup_save_dir: str,
    year: int,
    month: int,
    db_url: str
) -> None:
    """Print configs in screen and write logs."""
    logger.info('# Load config')
    logger.info('Work dir                                : {}'.format(os.getcwd()))
    logger.info('Load artichoke base service config path : {}'.format(artichoke_base_service_config_file_path))
    logger.info('Backup save dir                         : {}'.format(backup_save_dir))
    logger.info('Backup time                             : {}/{:02d}'.format(year, month))
    logger.info('DB_URL                                  : {}'.format(db_url))


def read_site_sniffer(db):
    # Query sniffer mac from site info and return a tuple
    sql = """SELECT sniffer_id as sniffer, site_id FROM sniffer_info"""
    result = db.execute(sql)
    data = result.fetchall()
    sniffers = [idx[0] for idx in data]
    return tuple(sniffers), data


def show_table(sniffer, db, year, month):
    """
    Input
        sniffer     :: tuple
        year        :: int
        month       :: int
    In SQL,
        find 3 month ago partition table which is not empty.
        schemaname  :: schema name
        relname     :: table name
        n_live_tup  :: number of live rows in table (cached, not always true),
                       used to check table is non-empty
    """
    sql = """
            set session time zone 'Asia/Taipei';
            SELECT relname
              FROM pg_stat_user_tables
             WHERE schemaname = 'public'
               AND relname ~ 'rawdata_[a-z0-9]{12}_[0-9]{4}_[0-9]{2}'
               AND substring(relname,'[a-z0-9]{12}') IN %s
               AND replace(substring(relname,'_[0-9]{4}_[0-9]{2}'),'_','') = '%04d%02d'
          """ % (str(sniffer), year, month)
    result = db.execute(sql)
    data = result.fetchall()
    table_name = [idx[0] for idx in data]
    return table_name


def read_sql_tmpfile(query, db_engine, save_path, table_name):
    with bz2.BZ2File(save_path, 'w') as tmpfile:
        copy_sql = "COPY ({query}) TO STDOUT WITH CSV {head}".format(
            query=query, head="HEADER"
        )
        conn = db_engine.raw_connection()
        cur = conn.cursor()
        try:
            cur.copy_expert(copy_sql, tmpfile)
        except psycopg2.errors.SerializationFailure:
            logger.warning(f"This copy_sql is invalid, the table may not exist, sql: {copy_sql}")
        except Exception as e:
            logger.error(e)
            raise


def db_backup_main(data: list, backup_save_dir: str, table_list: list, engine):
    """
    db backup main function
    """
    total_cnt, done_cnt = len(data), 1
    logger.info('Need to backup table count : {}'.format(len(data)))
    logger.info("Start to db_backup.")
    for sniffer, site_id in data:
        logger.info(f"Progress {done_cnt}/{total_cnt} ... ")
        saved_table_name = ""
        for table_name in table_list:
            if sniffer in table_name and re.match("^(1[A-Z][0-9,A-Z]{2})", site_id):
                saved_table_name = table_name
                save_path = f'{backup_save_dir}/{site_id}_{saved_table_name.replace("rawdata_", "")}.bz2'
                continue
        if not saved_table_name:
            logger.warning(f"Sniffer {sniffer} not found with same table name.")
            done_cnt += 1
            continue
        if os.path.isfile(save_path):
            logger.warning(f"Skip {save_path} db_backup.")
            done_cnt += 1
            continue
        sql = """SELECT rt, sa, da, rssi, seqno, cname, pkt_type, pkt_subtype, channel, sniffer FROM {}""".format(saved_table_name)
        logger.info(f'Write file : {save_path}, sql : {sql}')
        read_sql_tmpfile(sql, engine, save_path, saved_table_name)
        done_cnt += 1
    logger.info("db_backup finished.")


def get_mapping_db_table(table_name: str, db_tables: list) -> Union[str, None]:
    reg = re.search('[a-z0-9]{12}', table_name)
    sniffer = reg.group() if reg else None
    if not sniffer:
        logger.info("Sniffer not found in this file name")
        return None
    for t in db_tables:
        if sniffer in t:
            logger.info(f"Map table {t} to drop.")
            return t
    logger.info(f"Sniffer {sniffer} can't map any table.")
    return None


def drop_table_db_operation(db, dropped_table: str):
    logger.info(f"Start to drop table {dropped_table}")
    sql = f"""DROP TABLE IF EXISTS {dropped_table}"""
    db.execute(sql)
    logger.info(f"Drop table {dropped_table} success.")


def drop_table_main(db, year: int, month: int, backup_save_dir_month: str) -> None:
    """
    Drop backup table main function.

    This function will do the following tasks:
    1. Check if the backup_save_dir_month exists.
    2. Get tables in database whose year and month matches input params.
    3. Get backup tables from input backup path.
    4. Map tables which are done backup and drop the table.
    """
    if not os.path.isdir(backup_save_dir_month):
        logger.info("This directory not found, skip drop process")
        return
    db_tables = show_table(read_site_sniffer(db)[0], db, year, month)
    backup_tables = os.listdir(backup_save_dir_month)
    for table_name in backup_tables:
        dropped_table = get_mapping_db_table(table_name, db_tables)
        if not dropped_table:
            continue
        drop_table_db_operation(db, dropped_table)

    # Drop other tables in this month.
    sql = """SELECT table_name FROM information_schema.tables
             WHERE table_name ~ '{}_{:02d}' and table_schema = 'public'""".format(year, month)
    exe = db.execute(sql)
    tables = exe.fetchall()
    tables = [i[0] for i in tables]
    for table_name in tables:
        drop_table_db_operation(db, table_name)
    db.commit()


def worker_db_backup(config_path: str, year: int, month: int) -> None:
    db_url = get_db_url(config_path)
    engine, db = create_db_obj(db_url)
    backup_save_dir = '/var/local/db_backup'
    backup_save_dir_month = backup_save_dir + '/{}_{:02d}'.format(year, month)
    if not check_backup_dir_exists(backup_save_dir, year, month):
        show_config_in_screen(
            config_path,
            backup_save_dir_month,
            year,
            month,
            db_url
        )
        # DB backup main process
        sniffer, data = read_site_sniffer(db)
        table_list = show_table(sniffer, db, year, month)
        db_backup_main(data, backup_save_dir_month, table_list, engine)
    # drop_table_main(db, year, month, backup_save_dir_month)


if __name__ == '__main__':
    @click.command()
    @click.option('--artichoke_base_service_config_file_path', default='./config/artichoke_base_service.ini', help='請填寫 artichoke_base_service.ini 檔案位置')
    @click.option('--backup_save_dir', default='/var/local/db_backup', help='請填寫要刪除的年月份資料之前備份的檔案路徑')
    @click.option('--year', default=None, help='請填寫要備份的年份')
    @click.option('--month', default=None, help='請填寫要備份的月份')
    @click.option('--drop', default=True, help='是否刪除表格')
    def run(
        artichoke_base_service_config_file_path,
        backup_save_dir,
        year,
        month,
        local,
        drop
    ) -> None:
        # TODO Fix force backup feature.
        year, month = get_specified_year_month(year, month)
        db_url = get_db_url(artichoke_base_service_config_file_path)
        engine, db = create_db_obj(db_url)
        backup_save_dir_month = backup_save_dir + '/{}_{:02d}'.format(year, month)
        if not check_backup_dir_exists(backup_save_dir, year, month):
            show_config_in_screen(
                artichoke_base_service_config_file_path,
                backup_save_dir_month,
                year,
                month,
                db_url
            )
            # DB backup main process
            sniffer, data = read_site_sniffer(db)
            table_list = show_table(sniffer, db, year, month)
            db_backup_main(data, backup_save_dir_month, table_list, engine)
        if drop:
            drop_table_main(db, year, month, backup_save_dir_month)

    run()
