"""
Definitions for site related CRUD operations.

History:
2021/08/09 Created by Patrick
"""
import re
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.sql import exists
from traceback import format_exc
from logging import config as logger_config
from logging import getLogger
from app.core.core_config import settings
from fastapi import HTTPException
from app.schemas.sniffer import SnifferInfo, RssiMonitorConfigSniffer
from app.api.api_v1.endpoints.utils.exceptions import ArtichokeException

logger_config.dictConfig(settings.LOGGER_CONF)
logger = getLogger(__name__)


def get_specified_sniffer(
    db: Session,
    sniffer_id: str
) -> SnifferInfo:
    sql_stmt = f"""
        SELECT site_id, sniffer_id, is_active, rssi, machine_area, machine_location, ip, dns,
        network_type, ups_is_active, wifi_no, wifi_mac, sniffer_no, gateway
        FROM sniffer_info
        WHERE sniffer_id = '{sniffer_id}'
    """
    exe = db.execute(sql_stmt)
    result = exe.fetchone()
    if not result:
        logger.error(f"Sniffer id: {sniffer_id} not found.")
        raise ArtichokeException(f"Sniffer id: {sniffer_id} not found.")
    site_id, sniffer_id, is_active, rssi, machine_area, machine_location, ip, dns, \
        network_type, ups_is_active, wifi_no, wifi_mac, sniffer_no, gateway = result
    sniffer = SnifferInfo(
        site_id=site_id, sniffer_id=sniffer_id, is_active=is_active, rssi=rssi,
        machine_area=machine_area, machine_location=machine_location, ip=ip, dns=dns,
        network_type=network_type, ups_is_active=ups_is_active, wifi_no=wifi_no, wifi_mac=wifi_mac,
        sniffer_no=sniffer_no, gateway=gateway
    )
    return sniffer


def get_all_sniffers_in_site_by_sniffer(
    db: Session,
    sniffer_id: str
) -> List[SnifferInfo]:
    sql_stmt = f"""
        SELECT site_id, sniffer_id, is_active, rssi, machine_area, machine_location, ip, dns,
        network_type, ups_is_active, wifi_no, wifi_mac, sniffer_no, gateway
        FROM sniffer_info WHERE site_id = (
            SELECT site_id FROM sniffer_info WHERE sniffer_id = '{sniffer_id}'
        )
    """
    exe = db.execute(sql_stmt)
    result = exe.fetchall()
    if not result:
        logger.error(f"Sniffer id: {sniffer_id} not found.")
        raise ArtichokeException(f"Sniffer id: {sniffer_id} not found.")
    sniffers = [
        SnifferInfo(
            site_id=s[0], sniffer_id=s[1], is_active=s[2], rssi=s[3],
            machine_area=s[4], machine_location=s[5], ip=s[6], dns=s[7],
            network_type=s[8], ups_is_active=s[9], wifi_no=s[10],
            wifi_mac=s[11], sniffer_no=s[12], gateway=s[13]
        ) for s in result
    ]
    return sniffers


def insert_new_sniffer_info(
    db: Session,
    sniffer: SnifferInfo
) -> None:
    sniffer_values = sniffer.dict().values()
    sql_stmt = f"INSERT INTO sniffer_info VALUES {tuple(sniffer_values)}"
    db.execute(sql_stmt)
    db.commit()


def update_sniffer_info(
    db: Session,
    sniffer: SnifferInfo
) -> None:
    sniffer_values = sniffer.dict().values()
    site_id, sniffer_id, is_active, rssi, machine_area, machine_location, ip, dns, \
        network_type, ups_is_active, wifi_no, wifi_mac, sniffer_no, gateway = sniffer_values
    sql_stmt = f"""
        UPDATE sniffer_info SET site_id = '{site_id}', is_active = {is_active}, rssi = {rssi},
            machine_area = '{machine_area}', machine_location = '{machine_location}', ip = '{ip}', dns = '{dns}',
            network_type = '{network_type}', ups_is_active = {ups_is_active}, wifi_no = '{wifi_no}',
            wifi_mac = '{wifi_mac}', sniffer_no = '{sniffer_no}', gateway = '{gateway}'
        WHERE sniffer_id = '{sniffer_id}'
    """
    db.execute(sql_stmt)
    db.commit()


def delete_sniffer_by_sniffer_id(
    db: Session,
    sniffer_id: str
) -> None:
    sql_stmt = f"SELECT site_id FROM sniffer_info WHERE sniffer_id = '{sniffer_id}'"
    exe = db.execute(sql_stmt)
    result = exe.fetchall()
    site_id = result[0][0]
    sql_stmt = f"DELETE FROM sniffer_info WHERE sniffer_id = '{sniffer_id}'"
    db.execute(sql_stmt)
    sql_stmt = f"INSERT INTO sniffer_history VALUES ('{sniffer_id}', '{datetime.now()}', '{site_id}', null, false)"
    db.execute(sql_stmt)
    db.commit()


def change_sniffer_for_site(
    db: Session,
    sniffer_id: str,
    old_site_id: str,
    new_site_id: str
) -> None:
    sql_stmt = f"UPDATE sniffer_info SET site_id = '{new_site_id}' WHERE sniffer_id = '{sniffer_id}'"
    db.execute(sql_stmt)
    sql_stmt = f"INSERT INTO sniffer_history VALUES ('{sniffer_id}', '{datetime.now()}', '{old_site_id}', '{new_site_id}', true)"
    db.execute(sql_stmt)
    db.commit()


def change_is_active_status(
    db: Session,
    sniffer_id: str,
    is_active: bool
) -> None:
    sql_stmt = f"UPDATE sniffer_info SET is_active = {is_active} WHERE sniffer_id = '{sniffer_id}'"
    db.execute(sql_stmt)
    db.commit()


def insert_new_rssi_sniffer_info(
    db: Session,
    new_rssi_sniffer: RssiMonitorConfigSniffer
) -> None:
    logger.info("Start insert new rssi sniffer info")
    rssi_sniffer_values = new_rssi_sniffer.dict().values()
    sql_stmt = f"INSERT INTO rssi_monitor_sniffer_info VALUES {tuple(rssi_sniffer_values)}"
    db.execute(sql_stmt)
    db.commit()
    logger.info("Insert new rssi sniffer info success.")
