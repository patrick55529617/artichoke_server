# -*- coding: utf-8 -*-
#!/usr/bin/env python3


import os, sys
import logging
import datetime
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import sqlalchemy.exc
import pandas as pd
import numpy as np
import math

import click

logger = logging.getLogger(__name__)

def read_active_site_info(db_url, store_type=None, site_id=None):
    # Read active site and Hoi (1S01 2F & onsite & area)
    sql = """select * from site_info 
            where (is_active=true or is_released=true) 
            """
    if store_type:
        sql += """and channel='{}' """.format(store_type)
    if site_id:
        sql += """and site_id='{}' """.format(site_id)
    data = pd.read_sql(sql=sql, con=db_url).set_index('site_id')
    return data

def create_newyear_rawdata_table(db_url, year, **kwargs):
    df_sites = read_active_site_info(db_url)
    for sid, site in df_sites.iterrows():
        logger.info('Create {} table for {}-{}'.format(year, sid, site['sname']))
        for sniffer in site['sniffer']:
            create_rawdata_table(db_url, sniffer, year)
    return

def create_base_rawdata_table(db_url):
    try:
        engine = create_engine(db_url)
        sql = """CREATE TABLE IF NOT EXISTS rawdata
                        (
                            rt timestamp with time zone NOT NULL,
                            sa character(12) NOT NULL,
                            da character(12) NOT NULL,
                            rssi smallint NOT NULL,
                            seqno integer NOT NULL,
                            cname character varying(16) DEFAULT ''::character varying,
                            pkt_type smallint NOT NULL,
                            pkt_subtype smallint NOT NULL,
                            ssid character varying(32) DEFAULT ''::character varying,
                            channel smallint NOT NULL,
                            upload_time timestamp with time zone,
                            delivery_time timestamp with time zone,
                            sniffer character(12) COLLATE pg_catalog."default" NOT NULL
                        ) 
                        PARTITION BY LIST (sniffer);
                        """
        print('--------------')
        print(sql)
        print('--------------')
        engine.execute(sql)
    except sqlalchemy.exc.SQLAlchemyError as e:
        logger.warning('[SQL Error] {}'.format(e))
    except Exception as e:
        logger.exception(e)


def create_rawdata_table(db_url, sniffer, year, **kwargs):
    try:
        # Craete rawdata base table
        create_base_rawdata_table(db_url)

        engine = create_engine(db_url)

        # Create sniffer partition
        sql = """CREATE TABLE IF NOT EXISTS rawdata_{sniffer} PARTITION OF rawdata
                FOR VALUES IN ('{sniffer}')
                PARTITION BY RANGE (rt);
                """.format(sniffer=sniffer)
        print(sql)
        engine.execute(sql)

        # Create nested partition table
        create_rawdata_yearly_table(sniffer, engine, db_url, year, **kwargs)
        for n in range(1,13):
            print('--------------')
            print('Create {}-{:02d} rawdata table'.format(year, n))
            create_rawdata_monthly_table(sniffer, engine, db_url, year, month=n, **kwargs)
        
    except sqlalchemy.exc.SQLAlchemyError as e:    
        logger.warning('[SQL Error] {}'.format(e))
    except Exception as e:
        logger.exception(e)

def create_rawdata_yearly_table(sniffer, engine=None, db_url=None, year=2019, **kwargs):
    if engine is None:
        engine = create_engine(db_url)
    try:
        sql= """CREATE TABLE rawdata_{sniffer}_{year} PARTITION OF rawdata_{sniffer}
                FOR VALUES FROM ('{year}-01-01 00:00:00+08') TO ('{next_year}-01-01 00:00:00+8')
                PARTITION BY RANGE (rt);
             """.format(sniffer=sniffer, year=year, next_year=year+1)
        print(sql)
        engine.execute(sql)
    except sqlalchemy.exc.SQLAlchemyError as e:    
        logger.warning('[SQL Error] {}'.format(e))
    except Exception as e:
        logger.exception(e)    

def create_rawdata_monthly_table(sniffer, engine=None, db_url=None, year=2019, month=1, **kwargs):
    if engine is None:
        engine = create_engine(db_url)
    try:
        next_month_year = year if month<12 else (year+1)
        next_month = month % 12 + 1
            
        sql= """CREATE TABLE rawdata_{sniffer}_{year}_{month:02d} PARTITION OF rawdata_{sniffer}_{year}
                FOR VALUES FROM ('{year}-{month:02d}-01 00:00:00+08') TO ('{next_month_year}-{next_month:02d}-01 00:00:00+8'); 
                ALTER TABLE rawdata_{sniffer}_{year}_{month:02d} ADD PRIMARY KEY (rt, sa);
             """.format(sniffer=sniffer, year=year, next_month_year=next_month_year, month=month, next_month=next_month)
        print(sql)
        engine.execute(sql)
    except sqlalchemy.exc.SQLAlchemyError as e:    
        logger.warning('[SQL Error] {}'.format(e))
    except Exception as e:
        logger.exception(e) 

def add_site_info(db_url, **kwargs):
    if 'func' not in kwargs:
        kwargs['func'] = '{}_{}'.format(kwargs['city'].lower(), kwargs['channel'].lower())

    engine = create_engine(db_url)
    try:
        sql= text("""INSERT INTO site_info (site_id, country, sname, channel, open_hour, closed_hour, open_hour_wend, closed_hour_wend, sniffer, city_enc, func, rssi) 
                    VALUES(:site_id, :country, :site_name, :channel, :open_hour, :closed_hour, :open_hour_wend, :closed_hour_wend, ARRAY[:sniffer], :city, ARRAY[:func], ARRAY[:rssi])""")
        print(kwargs)
        print(sql)
        engine.execute(sql, **kwargs)
    except sqlalchemy.exc.SQLAlchemyError as e:    
        logger.warning('[SQL Error] {}'.format(e))
    except Exception as e:
        logger.exception(e)  

def create_site_counter_func(db_url, func, sniffer, rssi=-90):
    engine = create_engine(db_url)
    try:
        sql = '''CREATE FUNCTION public.{func}(
                    _timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
                    _timeto timestamp with time zone DEFAULT now(
                    ))
                    RETURNS TABLE("time" timestamp with time zone, customers bigint) 
                    LANGUAGE 'sql'
                
                    AS $BODY$
                    
                       SELECT * FROM public.counter('{sniffer}', {rssi}, _timefrom, _timeto, _random_rssi:={area_rssi}) as t;
                    
                    $BODY$;
                '''.format(func=func, sniffer=sniffer, rssi=rssi, area_rssi=rssi)
        print(sql)
        engine.execute(sql)
    except sqlalchemy.exc.SQLAlchemyError as e:
        logger.warning('[SQL Error] {}'.format(e))
    except Exception as e:
        logger.exception(e)
    return

def register_site_from_file(file, db_url, test, **kwargs):
    df = pd.read_excel(file, header=0, index_col=1)
    for sid, info in df.iterrows():
        if sid is np.nan:
            print('Empty row')
            break

        if type(sid) is float:
            sid = str(int(sid))

        if ('RSSI' not in info) or (info['RSSI'] is np.nan) or (math.isnan(info['RSSI'])):
            print('none of it')
            info['RSSI'] = -90

        info['Sniffer MAC'] = info['Sniffer MAC'].lower()
        func = '{}_{}'.format(info['City'].lower(), info['Channel'].lower())

        if test:
            sid = '{}-TEST'.format(sid)
            func = '{}_test'.format(func)

        add_site_info(db_url=db_url,
                      site_id=sid,
                      country='Taiwan',
                      site_name=info['門店'],
                      channel=info['Channel'],
                      open_hour='10:30:00+08' if info['Channel']=='HOLA' else '10:00:00+08',
                      closed_hour='22:00:00+08',
                      open_hour_wend='10:30:00+08' if info['Channel'] == 'HOLA' else '10:00:00+08',
                      closed_hour_wend='22:00:00+08',
                      sniffer=info['Sniffer MAC'],
                      city=info['City'],
                      func=func,
                      rssi=info['RSSI'])
        create_rawdata_table(db_url, info['Sniffer MAC'], datetime.datetime.now().year)
        create_site_counter_func(db_url, func, info['Sniffer MAC'], info['RSSI'])
    return

def set_privilege(db_url):
    engine = create_engine(db_url)
    try:
        sql = '''GRANT SELECT ON ALL TABLES IN SCHEMA public TO dw, echoi;'''
        print(sql)
        engine.execute(sql)
    except sqlalchemy.exc.SQLAlchemyError as e:
        logger.warning('[SQL Error] {}'.format(e))
    except Exception as e:
        logger.exception(e)
    return


if __name__ == '__main__':
    @click.command()
    @click.option('--db_url', default='postgresql+psycopg2://artichoke:edt-1234@10.101.2.18/artichoke', envvar='db_url', help='The PostgreSQL Server URL. (ex: postgresql+psycopg2://scott:tiger@localhost/mydatabase)')
    @click.option('--db_url_super', default='postgresql+psycopg2://postgres:atk-1234@10.101.2.18/artichoke')
    @click.option('--sniffer', '-s', default='1234567890ab', help='Sniffer mac(s) that used for wifi probe')
    @click.option('--year', default=2019, help='Year of rawdatat table to be created. Default is 2019')
    @click.option('--site_id', default='13112', help='Site ID')
    @click.option('--site_name', default='', help='Site name')
    @click.option('--channel', default=None, help='TLW | HOLA')
    @click.option('--open_hour', default='10:00:00+08', help='Open hour')
    @click.option('--country', default='Taiwan', help='Taiwan | China')
    @click.option('--city', '-c', default=None, help='City name spelled with alphabet')
    @click.option('--file', '-f', default=None, help='Site info excel file')
    @click.option('--test', '-t', is_flag=True, help='Create test site info ')
    def run(db_url, db_url_super, test, file=None, *args, **kwargs):
        if file is None:
            try:
                add_site_info(db_url, **kwargs)
                create_rawdata_table(db_url, **kwargs)
                if 'city' in kwargs and 'channel' in kwargs:
                    create_site_counter_func(db_url, '{}_{}'.format(kwargs['city'],kwargs['channel']), kwargs['sniffer'])
            except Exception as e:
               print(e)
        else:
            if not os.path.isfile(file):
                print('File "{}" does not exist!'.format(file))
                return
            print('File {} exists.'.format(file))
            register_site_from_file(file, db_url, test, **kwargs)
        set_privilege(db_url_super)
    run()
