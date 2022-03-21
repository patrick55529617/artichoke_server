# -*- coding: utf-8 -*-
# !/usr/bin/env python3
import os
import logging
from sqlalchemy import create_engine
from datetime import date, datetime, timedelta
import pandas as pd

# Configure logs
logger = logging.getLogger(__name__)


def read_released_site_info(db_url):
    sql = """SELECT * FROM site_info
             WHERE is_released = true or site_id='1A39'
          """
    data = pd.read_sql(sql=sql, con=db_url).set_index('site_id')
    return data


def daily_dwell_summary(engine, target_date, df_site, is_weekday):
    col_open_hour = 'open_hour' if is_weekday else 'open_hour_wend'
    col_closed_hour = 'closed_hour' if is_weekday else 'closed_hour_wend'
    for sid, site in df_site.iterrows():
        group_no = site['groups'][0]
        logger.info('[{}] group number: {}'.format(sid, group_no))
        for method in range(0,3):
            sql = '''INSERT INTO daily_dwell_sum
                SELECT '{sid}' as site_id, '{d}' as "date", {g_no} as agg_group_no, {m} as method, COALESCE(sum(v), 0) as value
                FROM heatmap_dwell('{sid}', '{d} {open}', '{d} {close}', {m}, agg_group_no:={g_no})'''\
                .format(sid=sid, d=target_date, m=method, g_no=group_no,
                        open=site[col_open_hour], close=site[col_closed_hour])
            logger.info(sql)
            try:
                engine.execute(sql)
                print('execute here')
            except Exception as e:
                logger.exception(e)


def daily_dwell(engine, target_date, df_site, is_weekday):
    col_open_hour = 'open_hour' if is_weekday else 'open_hour_wend'
    col_closed_hour = 'closed_hour' if is_weekday else 'closed_hour_wend'
    for sid, site in df_site.iterrows():
        group_no = site['groups'][0]
        logger.info('[{}] group number: {}'.format(sid, group_no))
        method = 0 #總停留時間
        sql = '''INSERT INTO daily_dwell
            SELECT '{sid}' as site_id, '{d}' as "date", {g_no} as agg_group_no, {m} as method, x, y, r as radius, v as value
            FROM heatmap_dwell('{sid}', '{d}', '{d}', {m}, agg_group_no:={g_no})'''\
            .format(sid=sid, d=target_date, m=method, g_no=group_no,
                    open=site[col_open_hour], close=site[col_closed_hour])
        logger.info(sql)
        try:
            engine.execute(sql)
            print('execute here')
        except Exception as e:
            logger.exception(e)


def worker_run_catnip_multi():
    db_url = 'postgresql+psycopg2://catnip:edt-1234@hoi.edt.testritegroup.com/catnip_multi'
    nday = 1
    iso_date = (date.today() - timedelta(nday)).strftime("%Y-%m-%d")
    is_weekday = datetime.strptime(iso_date, '%Y-%m-%d').weekday() < 5

    df_site = read_released_site_info(db_url)
    engine = create_engine(db_url)
    daily_dwell_summary(engine, iso_date, df_site, is_weekday)
    daily_dwell(engine, iso_date, df_site, is_weekday)
