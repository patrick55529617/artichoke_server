"""
Definitions for customer_count related CRUD operations.

History:
2021/08/24 Created by Patrick
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import date
from logging import config as logger_config
from logging import getLogger
from app.core.core_config import settings
from app.api.api_v1.endpoints.utils.exceptions import ArtichokeException
from fastapi import HTTPException
from app.schemas.customer_count import HourlyStatistic, DailyStatistic, CustomerCount, HistoryQuery
logger_config.dictConfig(settings.LOGGER_CONF)
logger = getLogger(__name__)


def get_realtime_report_by_site_id(
    db: Session,
    site_ids: str
) -> CustomerCount:
    site_ids = site_ids.split(",")
    site_ids = f"('{site_ids[0]}')" if len(site_ids) == 1 else str(tuple(site_ids))
    sql_stmt = f"""
        SET session time zone 'Asia/Taipei';
        SELECT site_id, ts_hour, count FROM customer_count
        WHERE site_id IN {site_ids} AND ts_hour > '{date.today()}'
        ORDER BY site_id
    """
    exe = db.execute(sql_stmt)
    result = exe.fetchall()
    sites = set(map(lambda x: x[0], result))
    group_by_site_id = sorted([[y for y in result if y[0]==x] for x in sites], key=lambda x: x[0])
    realtime_counts = [
        CustomerCount(
            site_id=site,
            data=[HourlyStatistic(hour=str(i[1]), count=i[2]) for i in data]
        ) for site, data in zip(sites, group_by_site_id)
    ]
    return realtime_counts


def get_history_report_by_site_ids(
    db: Session,
    history_query: HistoryQuery
) -> [CustomerCount]:
    site_ids, start_dt, end_dt = history_query.site_ids.split(","), history_query.start_dt, history_query.end_dt
    site_ids = f"('{site_ids[0]}')" if len(site_ids) == 1 else str(tuple(site_ids))
    sql_stmt = f"""
        SET session time zone 'Asia/Taipei';
        SELECT site_id, DATE(ts_hour) AS date, SUM(count) FROM customer_count
        WHERE site_id IN {site_ids} AND ts_hour BETWEEN '{start_dt}' AND '{end_dt} 23:59:59'
        GROUP BY site_id, date ORDER BY site_id, date
    """
    exe = db.execute(sql_stmt)
    result = exe.fetchall()
    sites = set(map(lambda x: x[0], result))
    group_by_site_id = sorted([[y for y in result if y[0]==x] for x in sites], key=lambda x: x[0])
    history_counts = [
        CustomerCount(
            site_id=site,
            data=[DailyStatistic(date=str(i[1]), count=i[2]) for i in data]
        ) for site, data in zip(sorted(sites), group_by_site_id)
    ]
    return history_counts
