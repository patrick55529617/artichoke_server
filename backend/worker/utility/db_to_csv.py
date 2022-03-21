# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
::BASH command::
> python3 db_to_csv.py --db_url <your DB url> --save_path <your path> --year 2018 --month 7 --backup
"""

import os
import os.path
import glob
import logging

import pandas as pd

from sqlalchemy import create_engine
import click

logger = logging.getLogger(__name__)

def read_site_sniffer(engine):
    # Query sniffer mac from site info and return a tuple
    sql = """SELECT unnest(sniffer) as sniffer FROM site_info"""
    data = pd.read_sql(sql, engine)
    return tuple(data['sniffer'].str.lower())

def show_table(sniffer, engine, year, month):
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
    data = pd.read_sql(sql, engine)
    return data['relname'].tolist()

def dump_to_csv(save_path, table_name, engine, chunksize, compress):
    """
        return  description
        -1      empty table
        1       check failed, that rows is not the same
        0       OK
    """
    # Read number of rows
    sql_total_rows = """SELECT count(*) FROM {}""".format(table_name)
    total_rows = pd.read_sql(sql_total_rows, engine)['count'][0]
    if total_rows == 0: # empty
        logger.warning("Empty table: {}".format(table_name))
        return -1

    # Query data
    save_file = os.path.join(save_path, table_name + ('.csv.bz2' if compress else '.csv'))
    sql_reader = """SELECT * FROM {}""".format(table_name)
    reader = pd.read_sql(sql_reader, engine, chunksize=chunksize)

    # First chunk save the header; otherwise skip it
    is_first_chunk = True
    for chunk in reader:
        chunk.to_csv(save_file, index=False, header=is_first_chunk, encoding='utf-8',
                     compression='bz2' if compress else None,
                     mode='w' if is_first_chunk else 'a')
        # compress, default 'infer' means no compression
        total_rows -= chunk.shape[0] # number of rows in this chunk
        is_first_chunk = False
    logger.info("Table {} saved.".format(table_name))

    # Check the result
    if total_rows:
        logger.error("Check {} failed! # rows is not the same DB - CSV = {}".format(table_name, total_rows))
        return 1
    return 0

def truncate_table(table_name, engine):
    sql = """TRUNCATE ONLY {}""".format(table_name)
    with engine.begin() as conn:
        _ = conn.execute(sql)
    logger.info("Truncate the table {}".format(table_name))

def show_backup_table(save_path, year, month):
    file_rule = os.path.join(save_path, "rawdata_*_%d_%02d.*" %(year, month))
    file_list = glob.glob(file_rule)
    mapping_fn = lambda x: os.path.basename(x).split('.', maxsplit=1)[0]
    table_list = list(map(mapping_fn, file_list))
    return table_list

def remove_data(engine, save_path, year, month):
    # Check file has been backup.
    table_list = show_backup_table(save_path, year, month)
    for table in table_list:
        truncate_table(table, engine)

def simplify_data(engine, save_path, year, month):
    # Check file has been backup.
    table_list = show_backup_table(save_path, year, month)
    # Simplify: Remove Google and iOS random mac
    for table in table_list:
        sql = "SELECT 1 FROM {} WHERE cname = ANY(ARRAY['Google_Random', 'iOS_Random']) LIMIT 1".format(table)
        has_random_mac = not pd.read_sql(sql, engine).empty
        if not has_random_mac:
            logger.info('Table {} has not random mac-address.'.format(table))
            continue
        with engine.begin() as conn:
            sql = "TRUNCATE public.backup_rawdata;"
            _ = conn.execute(sql)
            sql = "INSERT INTO public.backup_rawdata SELECT * FROM {} WHERE cname != ALL(ARRAY['Google_Random', 'iOS_Random']);".format(table)
            _ = conn.execute(sql)
            sql = "TRUNCATE {};".format(table)
            _ = conn.execute(sql)
            sql = "INSERT INTO {} SELECT * FROM public.backup_rawdata;".format(table)
            _ = conn.execute(sql)
            logger.info('Removed random mac for {}'.format(table))

if __name__ == '__main__':
    LOG_FORMAT = '%(asctime)-15s %(levelname)s %(processName)s-%(threadName)s-%(funcName)s, line %(lineno)d:%(message)s'
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    @click.command()
    @click.option('--db_url', envvar='db_url',
                  help='The PostgreSQL Server URL. (ex: postgresql+psycopg2://scott:tiger@localhost/mydatabase)')
    @click.option('--save_path', envvar='save_path', help='Path for saving backup file.')
    @click.option('--year', default=2017, help='Year')
    @click.option('--month', default=12, help='Month')
    @click.option('--backup', is_flag=True, help='Backup compress file')
    @click.option('--shrink', is_flag=True, help='Shrink DB table')
    @click.option('--truncate', is_flag=True, help='Truncate DB table')
    @click.option('--chunksize', envvar='chunksize', default=10000, help='Number of rows per query.')

    def main(db_url, save_path, year, month, backup, shrink, truncate, chunksize, compress=True):

        if save_path is None:
            logger.error("No input variable: save_path")
            exit(1)
        if db_url is None:
            logger.error("No input variable: db_url")
            exit(1)

        engine = create_engine(db_url)
        logger.info('DB: %s', engine)

        if backup:
            logger.info("Starting backup DB table")
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            sniffer = read_site_sniffer(engine)
            table_list = show_table(sniffer, engine, year, month)
            for table_name in table_list:
                # save to a (compressed) csv
                dump_to_csv(save_path, table_name, engine, chunksize, compress)

        if shrink:
            logger.info("Starting shrink DB table")
            simplify_data(engine, save_path, year, month)

        if truncate:
            logger.info("Starting shrink DB table")
            remove_data(engine, save_path, year, month)

    main()
