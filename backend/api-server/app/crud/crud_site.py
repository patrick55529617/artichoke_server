"""
Definitions for site related CRUD operations.

History:
2021/08/09 Created by Patrick
"""
import os
import csv
import shutil
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from logging import config as logger_config
from logging import getLogger
from app.core.core_config import settings
from app.api.api_v1.endpoints.utils.exceptions import ArtichokeException
from fastapi import HTTPException
from app.schemas.site import SiteInfo, SiteInfoWithSniffer, RssiMonitorConfigSite
logger_config.dictConfig(settings.LOGGER_CONF)
logger = getLogger(__name__)


def get_all_site_infos(
    db: Session,
) -> List[SiteInfo]:
    sql_stmt = """
        SELECT site_id, sname, channel, open_hour, closed_hour, open_hour_wend, closed_hour_wend,
        is_released, android_rate, wifi_rate, region, "group", alg_version, alg_params FROM site_info
        ORDER BY site_id
    """
    logger.info("Start get site info")
    exe = db.execute(sql_stmt)
    result = exe.fetchall()
    sites = list()
    for site in result:
        site_id, sname, channel, open_hour, closed_hour, open_hour_wend, closed_hour_wend, \
        is_released, android_rate, wifi_rate, region, group, alg_version, alg_params = site
        open_hour, closed_hour, open_hour_wend, closed_hour_wend = str(open_hour), str(closed_hour), str(open_hour_wend), str(closed_hour_wend)
        sites.append(
            SiteInfo(
                site_id=site_id, sname=sname, channel=channel, open_hour=open_hour, closed_hour=closed_hour, open_hour_wend=open_hour_wend, closed_hour_wend=closed_hour_wend,
                is_released=is_released, android_rate=android_rate, wifi_rate=wifi_rate, region=region, group=group, alg_version=alg_version, alg_params=alg_params
            )
        )
    logger.info("Get site info success")
    return sites


def get_one_site_info_by_site_id(
    db: Session,
    site_id: str
) -> SiteInfo:
    logger.info("Start get one site info")
    sql_stmt = f"""
        SELECT si_i.site_id, si_i.sname, si_i.channel, si_i.open_hour, si_i.closed_hour, si_i.open_hour_wend, si_i.closed_hour_wend,
        si_i.is_released, si_i.android_rate, si_i.wifi_rate, si_i.region, si_i."group", si_i.alg_version, si_i.alg_params, si_i.tel, si_i.hostname,
        sn_i.sniffer_id, sn_i.rssi
        FROM site_info AS si_i
        FULL JOIN (SELECT site_id, array_agg(sniffer_id) AS sniffer_id, array_agg(rssi) AS rssi FROM sniffer_info GROUP BY site_id)
        AS sn_i ON si_i.site_id = sn_i.site_id WHERE si_i.site_id = '{site_id}'
    """
    exe = db.execute(sql_stmt)
    result = exe.fetchall()
    if not result:
        raise ArtichokeException('Site id not found.')
    site_id, sname, channel, open_hour, closed_hour, open_hour_wend, closed_hour_wend, \
    is_released, android_rate, wifi_rate, region, group, alg_version, alg_params, tel, hostname, sniffer_ids, rssi = result[0]
    open_hour, closed_hour, open_hour_wend, closed_hour_wend = str(open_hour), str(closed_hour), str(open_hour_wend), str(closed_hour_wend)
    logger.info("Get one site info success")
    return SiteInfoWithSniffer(
        site_id=site_id, sname=sname, channel=channel, open_hour=open_hour, closed_hour=closed_hour, open_hour_wend=open_hour_wend, closed_hour_wend=closed_hour_wend,
        is_released=is_released, android_rate=android_rate, wifi_rate=wifi_rate, region=region, group=group,
        alg_version=alg_version, alg_params=alg_params, tel=tel, hostname=hostname, sniffer_ids=sniffer_ids, rssi=rssi
    )


def fuzzy_search_for_site_info(
    db: Session,
    sname: str
) -> List[SiteInfoWithSniffer]:
    logger.info("Start fuzzy search for site name.")
    sql_stmt = f"""
        SELECT si_i.site_id, si_i.sname, si_i.channel, si_i.open_hour, si_i.closed_hour, si_i.open_hour_wend, si_i.closed_hour_wend,
        si_i.is_released, si_i.android_rate, si_i.wifi_rate, si_i.region, si_i."group", si_i.alg_version, si_i.alg_params,
        si_i.tel, si_i.hostname, sn_i.sniffer_id, sn_i.rssi
        FROM site_info AS si_i
        FULL JOIN (SELECT site_id, array_agg(sniffer_id) AS sniffer_id, array_agg(rssi) AS rssi FROM sniffer_info GROUP BY site_id)
        AS sn_i ON si_i.site_id = sn_i.site_id WHERE si_i.sname LIKE '%{sname}%'
    """
    exe = db.execute(sql_stmt)
    result = exe.fetchall()
    sites = list()
    for site in result:
        site_id, sname, channel, open_hour, closed_hour, open_hour_wend, closed_hour_wend, \
        is_released, android_rate, wifi_rate, region, group, alg_version, alg_params, tel, hostname, sniffer_ids, rssi = site
        open_hour, closed_hour, open_hour_wend, closed_hour_wend = \
        str(open_hour), str(closed_hour), str(open_hour_wend), str(closed_hour_wend)
        sites.append(
            SiteInfoWithSniffer(
                site_id=site_id, sname=sname, channel=channel, open_hour=open_hour, closed_hour=closed_hour, open_hour_wend=open_hour_wend,
                closed_hour_wend=closed_hour_wend, is_released=is_released, android_rate=android_rate,
                wifi_rate=wifi_rate, region=region, group=group,
                alg_version=alg_version, alg_params=alg_params,
                tel=tel, hostname=hostname,
                sniffer_ids=sniffer_ids, rssi=rssi
            )
        )
    logger.info("Fuzzy search for site name success.")
    return sites


def insert_new_site_info(
    db: Session,
    new_site_info: SiteInfo
) -> None:
    logger.info("Start insert new site info.")
    alg_params = str(new_site_info.alg_params).replace("'", '"')
    sql_stmt = f"""
        INSERT INTO site_info VALUES ('{new_site_info.site_id}', '{new_site_info.sname}', '{new_site_info.channel}',
        '{new_site_info.open_hour}', '{new_site_info.closed_hour}', '{new_site_info.open_hour_wend}', '{new_site_info.closed_hour_wend}',
        {new_site_info.is_released}, {new_site_info.android_rate}, {new_site_info.wifi_rate},
        '{new_site_info.region}', '{new_site_info.group}', {new_site_info.alg_version}, '{alg_params}',
        '{new_site_info.tel}', '{new_site_info.hostname}')
    """
    db.execute(sql_stmt)
    db.commit()
    logger.info("Insert new site info success.")


def update_site_info(
    db: Session,
    site_id: str,
    new_site_info: SiteInfo
) -> None:
    logger.info("Start update one site info")
    if site_id != new_site_info.site_id:
        raise ArtichokeException("site_id not equal.")
    alg_params = str(new_site_info.alg_params).replace("'", '"')
    sql_stmt = f"""
        UPDATE site_info SET sname='{new_site_info.sname}', channel='{new_site_info.channel}',
        open_hour='{new_site_info.open_hour}' , closed_hour='{new_site_info.closed_hour}',
        open_hour_wend='{new_site_info.open_hour_wend}', closed_hour_wend='{new_site_info.closed_hour_wend}',
        is_released={new_site_info.is_released}, android_rate={new_site_info.android_rate}, wifi_rate={new_site_info.wifi_rate},
        region='{new_site_info.region}', "group"='{new_site_info.group}', alg_version={new_site_info.alg_version},
        alg_params='{alg_params}', tel='{new_site_info.tel}', hostname='{new_site_info.hostname}'
        WHERE site_id = '{site_id}'
    """
    db.execute(sql_stmt)
    db.commit()
    logger.info("Update one site info success.")


def delete_site_info(
    db: Session,
    site_id: str
) -> None:
    logger.info("Start delete one site info")
    sql_stmt = f"""DELETE FROM site_info WHERE site_id = '{site_id}'"""
    db.execute(sql_stmt)
    db.commit()
    logger.info("Delete one site success.")


def insert_new_rssi_site(
    db: Session,
    new_rssi_site: RssiMonitorConfigSite
) -> None:
    logger.info("Start insert new rssi site info")
    rssi_site_values = new_rssi_site.dict().values()
    sql_stmt = f"INSERT INTO rssi_monitor_site_info VALUES {tuple(rssi_site_values)}"
    db.execute(sql_stmt)
    db.commit()
    logger.info("Insert new rssi site info success.")


def update_site_office_hour(
    db: Session,
    csv_path: str
) -> None:
    logger.info("Start update office hour by csv.")
    DROP_FIRST_COLUMN_LINE = True
    try:
        with open(csv_path, "r") as buf:
            reader = csv.reader(buf, delimiter=',')
            for row in reader:
                if DROP_FIRST_COLUMN_LINE:
                    DROP_FIRST_COLUMN_LINE = False
                    continue
                site_id, _, open_hour, closed_hour, open_hour_wend, closed_hour_wend = row
                sql = f"""
                    UPDATE site_info
                    SET open_hour = '{open_hour}',
                    closed_hour = '{closed_hour}',
                    open_hour_wend = '{open_hour_wend}',
                    closed_hour_wend = '{closed_hour_wend}'
                    WHERE site_id = '{site_id}'
                """
                db.execute(sql)
            db.commit()
        os.remove(csv_path)
    except Exception as e:
        logger.error(e)
        raise ArtichokeException("CSV parse error.")
    logger.info("Update office hour by csv success.")
