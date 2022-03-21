# -*- coding: utf-8 -*-

"""
Definition of the sniffer router for the artichoke api service.

Description:
The schemas and routers of Sniffers are defined in here.

History:
2021/08/09 Created by Patrick
2021/10/07 Add Token Verification for Each Endpoint by Patrick
2021/10/18 POST /sniffer Add worker create_db_table task.
"""

from fastapi import APIRouter, HTTPException, Body, Depends
from rq import Queue
from redis import Redis
from typing import List, Optional
from app.core.db_session import get_db_session
from app.crud import crud_sniffer
from app.schemas.sniffer import SnifferInfo, RssiMonitorConfigSniffer
from app.core.core_config import settings
from logging import config as logger_config
from logging import getLogger
from sqlalchemy.orm import Session
from app.api.api_v1.endpoints.utils.exceptions import ArtichokeException
from app.api.api_v1.endpoints.utils.token_verification import login_token_verification

logger_config.dictConfig(settings.LOGGER_CONF)
logger = getLogger(__name__)

router: APIRouter = APIRouter()


@router.get(
    "/{sniffer_id}",
    dependencies=[Depends(login_token_verification)],
    tags=["sniffer"],
    responses={404: {"description": "Site Not Found"}},
    summary='查看單一 sniffer 資訊',
    description='輸入 sniffer_id, 只列出該隻 sniffer 相關資訊'
)
async def get_only_specified_sniffer(
    sniffer_id: str,
    db: Session = Depends(get_db_session),
) -> SnifferInfo:
    """To get specified one sniffer's information."""
    try:
        sniffer_info = crud_sniffer.get_specified_sniffer(db, sniffer_id)
        return sniffer_info
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)


@router.get(
    "/site/{sniffer_id}",
    dependencies=[Depends(login_token_verification)],
    tags=["sniffer"],
    responses={404: {"description": "Site Not Found"}},
    summary='查看 sniffer 所在店點之所有 sniffer 資訊',
    description='輸入 sniffer_id, 列出所有該門店 sniffer 資訊'
)
async def get_all_sniffer_info_in_site(
    sniffer_id: str,
    db: Session = Depends(get_db_session),
) -> List[SnifferInfo]:
    """To get all sniffer infos in the site by one sniffer_id."""
    try:
        site_with_sniffers = crud_sniffer.get_all_sniffers_in_site_by_sniffer(db, sniffer_id)
        return site_with_sniffers
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)


@router.post(
    "",
    dependencies=[Depends(login_token_verification)],
    tags=["sniffer"],
    responses={404: {"description": "Site Not Found"}},
    summary='新增 sniffer 資訊',
    description='在 body 欄位輸入 sniffer_id 相關資訊, 進行新增'
)
async def add_new_sniffer(
    db: Session = Depends(get_db_session),
    new_sniffer_info: SnifferInfo = Body(
        ...,
        example={
            "site_id": "1A01",
            "sniffer_id": "74da38db1f97",
            "is_active": True,
            "rssi": -98,
            "machine_area": "41號走道",
            "machine_location": "貨架",
            "ip": "10.28.1.231/24",
            "dns": "172.17.64.78,172.16.1.26",
            "network_type": "DHCP",
            "ups_is_active": True,
            "wifi_no": "48",
            "wifi_mac": "74da38db2019",
            "sniffer_no": "48",
            "gateway": "10.28.1.250"
        }
    ),
    year: Optional[str] = None
) -> str:
    """Insert new sniffer info, and create database rawdata tables."""
    crud_sniffer.insert_new_sniffer_info(db, new_sniffer_info)
    q = Queue(connection=Redis('redis', 6379), default_timeout=3600)
    q.enqueue(
        'utility.create_db_table.worker_create_db_table',
        settings.WORKER_CONFIG_PATH,
        new_sniffer_info.sniffer_id,
        year
    )
    return "Add new sniffer success."


@router.put(
    "/{sniffer_id}",
    dependencies=[Depends(login_token_verification)],
    tags=["sniffer"],
    responses={404: {"description": "Site Not Found"}},
    summary='修改 sniffer 資訊',
    description='在 body 欄位輸入 sniffer_id 相關資訊, 進行修改'
)
async def update_sniffer_info(
    sniffer_id: str,
    db: Session = Depends(get_db_session),
    sniffer_info: SnifferInfo = Body(
        ...,
        example={
            "site_id": "1A01",
            "sniffer_id": "74da38db1f97",
            "is_active": True,
            "rssi": -98,
            "machine_area": "41號走道",
            "machine_location": "貨架",
            "ip": "10.28.1.231/24",
            "dns": "172.17.64.78,172.16.1.26",
            "network_type": "DHCP",
            "ups_is_active": True,
            "wifi_no": "48",
            "wifi_mac": "74da38db2019",
            "sniffer_no": "48",
            "gateway": "10.28.1.250"
        }
    ),
) -> str:
    """Insert new sniffer info."""
    try:
        crud_sniffer.update_sniffer_info(db, sniffer_info)
        return "Update sniffer success."
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)


@router.delete(
    "/{sniffer_id}",
    dependencies=[Depends(login_token_verification)],
    tags=["sniffer"],
    responses={404: {"description": "Site Not Found"}},
    summary='刪除某隻 sniffer',
    description='輸入 sniffer_id, 移除該 sniffer 並紀錄於 sniffer_history 表'
)
async def delete_unused_sniffer(
    sniffer_id: str,
    db: Session = Depends(get_db_session),
) -> str:
    """Delete unused sniffer info."""
    try:
        crud_sniffer.delete_sniffer_by_sniffer_id(db, sniffer_id)
        return "Delete sniffer success."
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)


@router.put(
    "/change_site/{sniffer_id}",
    dependencies=[Depends(login_token_verification)],
    tags=["sniffer"],
    responses={404: {"description": "Site Not Found"}},
    summary='sniffer 更換門店',
    description='在 body 欄位輸入修改前後的 site_id, 進行修改, 並紀錄進 sniffer_history 表'
)
async def sniffer_change_site(
    sniffer_id: str,
    db: Session = Depends(get_db_session),
    old_site_id: str = Body(...),
    new_site_id: str = Body(...),
) -> str:
    """Change sniffer to another site."""
    try:
        crud_sniffer.change_sniffer_for_site(db, sniffer_id, old_site_id, new_site_id)
        return "Change sniffer site success."
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)


@router.put(
    "/active/{sniffer_id}",
    dependencies=[Depends(login_token_verification)],
    tags=["sniffer"],
    responses={400: {"description": "Sniffer Not Found"}},
    summary='sniffer 切換 is_active 狀態',
    description='在 body 欄位輸入 is_active 狀態進行修改'
)
async def change_sniffer_isactive_status(
    sniffer_id: str,
    db: Session = Depends(get_db_session),
    is_active: bool = Body(...)
) -> str:
    """Change sniffer is active status."""
    try:
        crud_sniffer.change_is_active_status(db, sniffer_id, is_active)
        return f"Change sniffer: {sniffer_id} is_active status to {is_active} success."
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)


@router.post(
    "/rssi_monitor",
    dependencies=[Depends(login_token_verification)],
    responses={400: {"description": "Sniffer Not Found"}},
    summary='設定 rssi monitor - sniffer 部分',
    description='輸入 rssi monitor 有關 sniffer 部分, 將設定儲存進資料庫內'
)
async def set_rssi_monitor_sniffer(
    db: Session = Depends(get_db_session),
    new_rssi_sniffer: RssiMonitorConfigSniffer = Body(
        ...,
        example={
            "site_id": "1A01",
            "sniffer_id": "74da38db1f97",
            "rssi_group": "-62,-64,-68"
        }
    )
) -> str:
    try:
        crud_sniffer.insert_new_rssi_sniffer_info(db, new_rssi_sniffer)
        return "Insert new rssi sniffer info success."
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)
