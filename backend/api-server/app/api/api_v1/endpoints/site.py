# -*- coding: utf-8 -*-

"""
Definition of the site router for the artichoke api service.

Description:
The schemas and routers of Site are defined in here.

History:
2021/08/09 Created by Patrick
2021/10/07 Add Token Verification for Each Endpoint by Patrick
"""

import shutil
from fastapi import APIRouter, HTTPException, Body, Depends, File, UploadFile
from app.core.db_session import get_db_session
from app.crud import crud_site
from app.schemas.site import SiteInfo, SiteInfoWithSniffer, RssiMonitorConfigSite
from app.core.core_config import settings
from app.api.api_v1.endpoints.utils.exceptions import ArtichokeException
from app.api.api_v1.endpoints.utils.token_verification import login_token_verification
from app.api.api_v1.endpoints.utils.api_requests import get_frp_status
from logging import config as logger_config
from logging import getLogger
from sqlalchemy.orm import Session

logger_config.dictConfig(settings.LOGGER_CONF)
logger = getLogger(__name__)

router: APIRouter = APIRouter()


@router.get(
    "",
    dependencies=[Depends(login_token_verification)],
    tags=["site"],
    responses={400: {"description": "Site Not Found"}},
    summary='列出所有門店資訊',
    description='列出所有門店資訊, 不需任何參數',
    deprecated=True
)
async def get_all_site_infos(
    db: Session = Depends(get_db_session)
) -> [SiteInfo]:
    """To get all site's information."""
    sites = crud_site.get_all_site_infos(db)
    return sites


@router.get(
    "/{site_id}",
    dependencies=[Depends(login_token_verification)],
    tags=["site"],
    responses={400: {"description": "Site Not Found"}},
    summary='列出特定門店資訊',
    description='輸入 site_id, 列出該門店資訊'
)
async def get_one_site_info(
    site_id: str,
    db: Session = Depends(get_db_session),
) -> SiteInfoWithSniffer:
    """To get specified one site's information."""
    try:
        site = crud_site.get_one_site_info_by_site_id(db, site_id)
        return site
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)


@router.get(
    "/blur/{sname}",
    dependencies=[Depends(login_token_verification)],
    tags=["site"],
    responses={400: {"description": "Site Not Found"}},
    summary='使用模糊的店點名稱搜尋門店資訊',
    description='輸入 sname, 列出可能的所有門店資訊'
)
async def get_site_info_by_blur_search(
    sname: str,
    db: Session = Depends(get_db_session),
) -> [SiteInfoWithSniffer]:
    """To get specified one site's information."""
    sites = crud_site.fuzzy_search_for_site_info(db, sname)
    return sites


@router.post(
    "",
    dependencies=[Depends(login_token_verification)],
    tags=["site"],
    responses={400: {"description": "Site Not Found"}},
    summary='新增門店資訊',
    description='在 body 欄位輸入門店資訊進行新增'
)
async def add_new_site(
    db: Session = Depends(get_db_session),
    new_site_info: SiteInfo = Body(
        ...,
        example={
            "site_id": "1A01",
            "sname": "TLW桃園南崁店",
            "channel": "TLW",
            "open_hour": "10:00:00+08",
            "closed_hour": "21:00:00+08",
            "open_hour_wend": "10:00:00+08",
            "closed_hour_wend": "21:00:00+08",
            "is_released": True,
            "android_rate": 0.62,
            "wifi_rate": 0.66,
            "region": "Northern",
            "group": "標準店",
            "alg_version": 2,
            "alg_params": {
                "model_slope": 99.9832,
                "manual_slope": 178.5654,
                "model_intercept": 1101.3628,
                "model_upper_limit": 2805.7401
            },
            "tel": "03-321-1000",
            "hostname": "Nankan"
        }
    ),
) -> None:
    """Insert new site info to database."""
    crud_site.insert_new_site_info(db, new_site_info)
    return "Add New site_info Success."


@router.put(
    "/{site_id}",
    dependencies=[Depends(login_token_verification)],
    tags=["site"],
    responses={400: {"description": "Site Not Found"}},
    summary='修改門店資訊',
    description='在 body 欄位輸入門店資訊進行修改'
)
async def update_one_site_info(
    site_id: str,
    db: Session = Depends(get_db_session),
    new_site_info: SiteInfo = Body(
        ...,
        example={
            "site_id": "1A01",
            "sname": "TLW桃園南崁店",
            "channel": "TLW",
            "open_hour": "10:00:00+08",
            "closed_hour": "21:00:00+08",
            "open_hour_wend": "10:00:00+08",
            "closed_hour_wend": "21:00:00+08",
            "is_released": True,
            "android_rate": 0.62,
            "wifi_rate": 0.66,
            "region": "Northern",
            "group": "標準店",
            "alg_version": 2,
            "alg_params": {
                "model_slope": 99.9832,
                "manual_slope": 178.5654,
                "model_intercept": 1101.3628,
                "model_upper_limit": 2805.7401
            },
            "tel": "03-321-1000",
            "hostname": "Nankan"
        }
    )
) -> str:
    """To update specified one site's information."""
    try:
        crud_site.update_site_info(db, site_id, new_site_info)
        return "Update site_info Success."
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)


@router.delete(
    "/{site_id}",
    dependencies=[Depends(login_token_verification)],
    tags=["site"],
    responses={400: {"description": "Site Not Found"}},
    summary='刪除門店資訊',
    description='輸入 site_id, 刪除該門店資訊'
)
async def close_site(
    site_id: str,
    db: Session = Depends(get_db_session)
) -> str:
    """To delete specified one site."""
    try:
        crud_site.delete_site_info(db, site_id)
        return "Delete site_info Success."
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)


@router.get(
    "/frp/{site_id}",
    responses={400: {"description": "Site Not Found"}},
    summary='確認門店的設備是否已有連上 frp',
    description='輸入 site_id, 確認門店的設備是否已有連上 frp, 由於是暫時給門店人員使用, 所以先不綁 token'
)
async def check_frp_status(site_id: str) -> dict:
    try:
        connect_success = get_frp_status(site_id)
        if connect_success:
            return {"site_id": site_id, "status": "已連線"}
        else:
            return {"site_id": site_id, "status": "未連線"}
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)


@router.post(
    "/rssi_monitor",
    dependencies=[Depends(login_token_verification)],
    responses={400: {"description": "Site Not Found"}},
    summary='設定 rssi monitor - site 部分',
    description='輸入 rssi monitor 有關 site 部分, 將設定儲存進資料庫內'
)
async def set_rssi_monitor_site(
    db: Session = Depends(get_db_session),
    new_rssi_site: RssiMonitorConfigSite = Body(
        ...,
        example={
            "site_id": "1G55",
            "sname": "TLW苓雅三多店",
            "android_rate": 0.35,
            "wifi_rate": 0.66,
            "day_from": "2021-10-30"
        }
    )
) -> str:
    try:
        crud_site.insert_new_rssi_site(db, new_rssi_site)
        return "Insert rssi site info success."
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)


@router.post(
    "/change_office_hour",
    dependencies=[Depends(login_token_verification)],
    responses={400: {"description": "Site Not Found"}},
    summary='批次修改營業時間',
    description='吃一份營業時間表(csv 檔)，並修改表內全部門店的營業時間'
)
async def create_upload_file(
    db: Session = Depends(get_db_session),
    file: UploadFile = File(...)
) -> str:
    if not file.filename.endswith(".csv"):
        logger.error("Input invalid file type.")
        return HTTPException(status_code=400, detail="Input invalid file type.")
    with open(file.filename, "wb") as buf:
        shutil.copyfileobj(file.file, buf)
    try:
        crud_site.update_site_office_hour(db, file.filename)
    except ArtichokeException as e:
        return HTTPException(status_code=400, detail=e.msg)
    return "Update office hour by csv success."
