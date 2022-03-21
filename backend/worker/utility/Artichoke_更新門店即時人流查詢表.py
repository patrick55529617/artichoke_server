#!/usr/bin/env python
# coding: utf-8

import os, sys
import pandas as pd
import time, pytz
import click
import bz2
import logging.handlers
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from exchangelib import HTMLBody
from textwrap import dedent
import logging
import logging.config
import configparser

##################################################################
# Config
##################################################################
is_dev = None

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

def artichoke_log(str):
    logger.info(str)
    return

def generate_view_sql(channel, site_id_filter):
    # 門店資訊
    if is_dev:
        post_fix = '_int'
        base_filter = f"(is_released OR (site_id = '{is_dev}' AND {site_id_filter})) AND {site_id_filter}"
    else:
        post_fix = ''
        base_filter = f"is_released AND {site_id_filter}"

    sql = f"""
    SELECT site_id, func, sniffer, open_hour, closed_hour, open_hour_wend, closed_hour_wend
        , date_part('hour'::text, open_hour)::integer open_hour_int
        , date_part('hour'::text, closed_hour)::integer closed_hour_int
        , date_part('hour'::text, open_hour_wend)::integer open_hour_wend_int
        , date_part('hour'::text, closed_hour_wend)::integer closed_hour_wend_int
    FROM site_info 
    WHERE {base_filter} 
    ORDER BY site_id"""
    
    artichoke_log(
    dedent(
    f"""
    #Excute SQL :
    {sql}"""
    )
    )

    site_df = pd.read_sql(sql,engine)

    site_id = site_df['site_id'].iloc[0]
    func = site_df['func'].iloc[0][0]
    sniffer = site_df['sniffer'].iloc[0][0]

    msg = f"""
    Total site : {len(site_df)}
    First site_id : {site_id}
    First func : {func}
    First sniffer : {sniffer}
    """
    artichoke_log(dedent(msg))

    sql_template = """
        UNION
            SELECT '{site_id}'::text AS site_id,
                {func}."time" AS ts_hour,
                {func}.customers AS count
            FROM {func}(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) {func}("time", customers)
            WHERE date_part('hour'::text, timezone('Asia/Taipei'::text, {func}."time"))::integer >= {open_hour_min}
                AND date_part('hour'::text, timezone('Asia/Taipei'::text, {func}."time"))::integer < {close_hour_max}
    """

    sql_template_list = []
    view_name = f'customer_count_{channel}{post_fix}'
    
    sql = """
    CREATE OR REPLACE VIEW public.{view_name} AS

        SELECT tab.site_id,
            tab."time" AS ts_hour,
            tab.count
        FROM ( 
            SELECT people_count.site_id,
                people_count."time",
                people_count.count
            FROM people_count
            WHERE date_part('hour'::text, timezone('Asia/Taipei'::text, people_count."time"))::integer >= 9 
                AND date_part('hour'::text, timezone('Asia/Taipei'::text, people_count."time"))::integer <= 21

            {sql_template_list_str}
        ) tab           
    ;

    ALTER TABLE public.{view_name}
        OWNER TO artichoke;

    GRANT SELECT ON TABLE public.{view_name} TO dw;
    GRANT SELECT ON TABLE public.{view_name} TO shiny;
    GRANT ALL ON TABLE public.{view_name} TO artichoke;
    GRANT SELECT ON TABLE public.{view_name} TO echoi;
    """


    for idx, row in site_df.iterrows():
        site_id = row['site_id']
        
        if '-' in site_id:
            if '-Pi' in site_id:
                new_site_id = site_id.replace('-Pi','')
                artichoke_log(dedent(f"""site_id special rule detect!!! modify {site_id} to {new_site_id} """))
                site_id = new_site_id
            else:
                artichoke_log(dedent(f"""site_id special rule detect!!! {site_id} ignore """))
        
        sql_template_list.append(sql_template.format(site_id=site_id
                                 , func=row['func'][0]
                                 , open_hour_min=min(row['open_hour_int'],row['open_hour_wend_int'])
                                 , close_hour_max=max(row['closed_hour_int'],row['closed_hour_wend_int'])
                                ))

    sql = sql.format(sql_template_list_str='\n'.join(sql_template_list),
                    view_name=view_name)
    
    artichoke_log(f"\n#Create or replace view : {view_name}")

    return sql

def generate_view():
    post_fix = ''
    if is_dev:
        post_fix = '_int'
    
    # Each channel view    
    for key in site_id_filter.keys():
        sql_filter = site_id_filter[key]
        artichoke_log(dedent(f"""
        ====================================================================================================
        = Generate channel view with sql_filter : {sql_filter}
        ====================================================================================================
        """
             ))
        view_sql = generate_view_sql(key,sql_filter)
        artichoke_log(dedent(view_sql))
        
        engine.execute(dedent(view_sql))

        
    # All channel view    
    view_name = 'customer_count'
    channel_view_name_list = []

    for key in site_id_filter.keys():
        view = f'        SELECT * FROM customer_count_{key}{post_fix}'
        channel_view_name_list.append(view)
    channel_view_sql = """
        UNION
    """.join(channel_view_name_list)
        
    sql = f"""
    CREATE OR REPLACE VIEW public.{view_name}{post_fix} AS
        SELECT tab.site_id,
            tab.ts_hour,
            tab.count
        FROM (
    {channel_view_sql}
        ) tab
    ;

    ALTER TABLE public.{view_name}
        OWNER TO artichoke;

    GRANT SELECT ON TABLE public.{view_name}{post_fix} TO dw;
    GRANT SELECT ON TABLE public.{view_name}{post_fix} TO shiny;
    GRANT ALL ON TABLE public.{view_name}{post_fix} TO artichoke;
    GRANT SELECT ON TABLE public.{view_name}{post_fix} TO echoi;
    """

    artichoke_log(dedent(f"""
    ====================================================================================================
    = Generate all channel view ... 
    ====================================================================================================

    #Excute SQL :
    {sql}
    """
    ))
    
    engine.execute(dedent(sql))

def run(artichoke_base_service_config_file_path):
    global site_id_filter, engine
    
    ##################################################################
    # Load and setup config
    ##################################################################

    logger.info('# Load config')
    logger.info('Work dir                                : {}'.format(os.getcwd()))
    logger.info('Load artichoke base service config path : {}'.format(artichoke_base_service_config_file_path))

    # base service config
    config = configparser.ConfigParser()
    config.read([artichoke_base_service_config_file_path])

    # util config
    db_url = config['ARTICHOKE']['DB_URL_ADMIN']
    engine = create_engine(db_url)

    is_dev_hint_msg = "Create  customer int view!" if is_dev else "Create production customer view"
    logger.info('DB_URL_ADMIN                            : {}'.format(config['ARTICHOKE']['DB_URL_ADMIN']))
    logger.info('is_dev                                  : {} ({})'.format(is_dev, is_dev_hint_msg))

    ######################################################################################
    # Update each channel customer count view and all channel union customer count view
    ######################################################################################

    # 通路，需要更新到最新狀態
    site_id_filter = {
        'tlw' :"site_id ~ '^(1A|1G)'",
        'hola':"(site_id ~ '^(1B)' OR site_id IN ('1C03-area'))",
        'hoi' :"site_id ~ '^(1S)'",
        'cb'  :"site_id ~ '^(1K)'"
    }
    
    generate_view()


if __name__ == '__main__':
    @click.command()
    @click.option('-p', '--config_file_path', default='./config/artichoke_base_service.ini', help='請填寫 artichoke_base_service.ini 檔案位置')
    @click.option('-d', '--dev', type=str, help='更新 customer_view_int 請填寫新門店 SITE_ID ')
    def main(dev, config_file_path=None):
        global is_dev
        
        is_dev = dev
        run(config_file_path)

    main()
