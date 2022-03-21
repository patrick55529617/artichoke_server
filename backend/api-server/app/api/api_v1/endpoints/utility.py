# -*- coding: utf-8 -*-

"""
Definition of the utility script router for the artichoke api service.

Description:
The schemas and routers of utility are defined in here.

History:
2021/08/27 Created by Patrick
2021/10/07 Add Token Verification for Each Endpoint by Patrick
"""

from redis import Redis
from rq import Queue
from fastapi import APIRouter, HTTPException, Body, Depends
from app.core.db_session import get_db_session
from app.crud import crud_site
from app.schemas.utility import (
    DailyReportInput,
    MissingRecordInput,
    EposRoutineInput,
    AlertWeeklyInput,
    DbRoutineInput,
    DbRoutineInputOneSite,
    DbBackupInput
)
from app.core.core_config import settings
from app.api.api_v1.endpoints.utils.exceptions import ArtichokeException
from app.api.api_v1.endpoints.utils.token_verification import login_token_verification
from logging import config as logger_config
from logging import getLogger
from sqlalchemy.orm import Session

logger_config.dictConfig(settings.LOGGER_CONF)
logger = getLogger(__name__)

router: APIRouter = APIRouter()


@router.post(
    "/daily_report",
    dependencies=[Depends(login_token_verification)],
    tags=["util"],
    responses={400: {"description": "Bad Request"}},
    summary='寄送 daily report',
    description='在 body 欄位輸入 target_date (若不指定需填寫 null, 不加引號) 和 nday, API server 會下指令給 worker 進行處理'
)
async def send_daily_report(
    db: Session = Depends(get_db_session),
    daily_report_input: DailyReportInput = Body(
        ...,
        example={
            "nday": 1,
            "target_date": "2021-08-22 OR null"
        }
    )
):
    q = Queue(connection=Redis('redis', 6379))
    result = q.enqueue(
        'utility.daily_report.send_daily_report',
        settings.WORKER_CONFIG_PATH,
        daily_report_input.nday,
        daily_report_input.target_date
    )
    logger.info(daily_report_input)
    return daily_report_input


@router.post(
    "/missing_record_detection",
    dependencies=[Depends(login_token_verification)],
    tags=["util"],
    responses={400: {"description": "Bad Request"}},
    summary='檢查是否有遺漏的 rawdata',
    description='在 body 欄位相對應的參數, 注意 target_date, site_id 可為空, API server 會下指令給 worker 進行處理'
)
async def check_missing_record(
    db: Session = Depends(get_db_session),
    missing_record_input: MissingRecordInput = Body(
        ...,
        example={
            "site_id": "1A01 OR null",
            "target_date": "2021-08-22 OR null",
            "nday": 1,
            "rday": 7,
            "tolerance": 5,
            "only_weekly": False
        }
    )
):
    q = Queue(connection=Redis('redis', 6379))
    result = q.enqueue(
        'utility.missing_record_detection.send_missing_record_email',
        settings.WORKER_CONFIG_PATH,
        missing_record_input.site_id,
        missing_record_input.target_date,
        missing_record_input.nday,
        missing_record_input.rday,
        missing_record_input.tolerance,
        missing_record_input.only_weekly
    )
    logger.info(missing_record_input)
    return missing_record_input


@router.post(
    "/epos_routine",
    dependencies=[Depends(login_token_verification)],
    tags=["util"],
    responses={400: {"description": "Bad Request"}},
    summary='epos routine',
    description='在 body 欄位相對應的參數, 注意 target_date, site_id 可為空, API server 會下指令給 worker 進行處理'
)
async def insert_epos_daily_to_db(
    db: Session = Depends(get_db_session),
    epos_routine_input: EposRoutineInput = Body(
        ...,
        example={
            "nday": 1,
            "target_date": "2021-08-22 OR null",
            "site_id": "1A01 OR null",
        }
    )
):
    q = Queue(connection=Redis('redis', 6379))
    q.enqueue(
        'utility.epos_routine.worker_run_epos_routine',
        settings.WORKER_CONFIG_PATH,
        epos_routine_input.nday,
        epos_routine_input.target_date,
        epos_routine_input.site_id
    )
    logger.info(epos_routine_input)
    return epos_routine_input


@router.post(
    "/alert_weekly",
    dependencies=[Depends(login_token_verification)],
    tags=["util"],
    responses={400: {"description": "Bad Request"}},
    summary='出每週一次的 alert 統計報表',
    description='輸入 start_time & end_time, 寄出在這區間的統計報表, 參數可為 null'
)
async def send_alert_weekly_email(
    db: Session = Depends(get_db_session),
    alert_weekly_input: AlertWeeklyInput = Body(
        ...,
        example={
            "start_time": "2021-08-30 08:00:00 OR null",
            "end_time": "2021-09-06 08:00:00 OR null"
        }
    )
):
    q = Queue(connection=Redis('redis', 6379))
    q.enqueue(
        'utility.alert_weekly_report.worker_run_alert_weekly_report',
        settings.WORKER_CONFIG_PATH,
        alert_weekly_input.start_time,
        alert_weekly_input.end_time
    )
    logger.info(alert_weekly_input)
    return alert_weekly_input


@router.post(
    "/db_routine",
    dependencies=[Depends(login_token_verification)],
    tags=["util"],
    responses={400: {"description": "Bad Request"}},
    summary='重新計算之前特定某天的人流數據',
    description='輸入指定日期，重新計算該天的人流數據，格式為 YYYY-MM-DD'
)
async def re_calculate_db_routine(
    db: Session = Depends(get_db_session),
    db_routine_input: DbRoutineInput = Body(
        ...,
        example={
            "specific_date": "2021-09-05"
        }
    )
):
    q = Queue(connection=Redis('redis', 6379), default_timeout=3600)
    q.enqueue(
        'worker_tmp_alg.worker_run_db_routine',
        db_routine_input.specific_date
    )
    logger.info(db_routine_input)
    return db_routine_input


@router.post(
    "/db_routine/{site_id}",
    dependencies=[Depends(login_token_verification)],
    tags=["util"],
    responses={400: {"description": "Bad Request"}},
    summary='重新計算之前特定某天, 某門店的人流數據',
    description='輸入 site_id 和指定日期，重新計算該天的人流數據，格式為 YYYY-MM-DD'
)
async def re_calculate_db_routine_one_site(
    db: Session = Depends(get_db_session),
    db_routine_input: DbRoutineInputOneSite = Body(
        ...,
        example={
            "specific_date": "2021-09-05",
            "site_id": "1A01"
        }
    )
):
    q = Queue(connection=Redis('redis', 6379), default_timeout=3600)
    q.enqueue(
        'worker_tmp_alg.worker_run_db_routine_one_site',
        db_routine_input.specific_date,
        db_routine_input.site_id
    )
    logger.info(db_routine_input)
    return db_routine_input


@router.post(
    "/missing_alarm",
    dependencies=[Depends(login_token_verification)],
    tags=["util"],
    responses={400: {"description": "Bad Request"}},
    summary='即時檢查線上人流系統是否有出問題',
    description='偵測及時人流'
)
async def send_missing_alarm_email(db: Session = Depends(get_db_session)):
    q = Queue(connection=Redis('redis', 6379), default_timeout=3600)
    q.enqueue('utility.artichoke_rawdata_missing_alarm.worker_send_missing_alarm')


@router.post(
    "/rssi_monitor",
    dependencies=[Depends(login_token_verification)],
    responses={400: {"description": "Bad Request"}},
    summary='RSSI monitor',
    description='RSSI monitor'
)
async def run_rssi_monitor(db: Session = Depends(get_db_session)):
    q = Queue(connection=Redis('redis', 6379), default_timeout=3600)
    q.enqueue(
        'utility.rssi_monitor.worker_run_rssi_monitor',
        settings.WORKER_CONFIG_PATH
    )


@router.post(
    "/db_backup",
    dependencies=[Depends(login_token_verification)],
    responses={400: {"description": "Bad Request"}},
    summary='人流數據資料備份',
    description='指定月份，進行該月的資料備份後，將表格刪除'
)
async def run_db_backup(
    db: Session = Depends(get_db_session),
    db_backup_input: DbBackupInput = Body(
        ...,
        example={
            "year": 2021,
            "month": 12
        }
    )
):
    q = Queue(connection=Redis('redis', 6379), default_timeout=14400)
    q.enqueue(
        'utility.Artichoke_db_backup.worker_db_backup',
        settings.WORKER_CONFIG_PATH,
        db_backup_input.year,
        db_backup_input.month
    )


@router.post(
    "/catnip/db_routine_multi",
    dependencies=[Depends(login_token_verification)],
    responses={400: {"description": "Bad Request"}},
    summary='Catnip db_routine_multi',
    description='Catnip db_routine_multi'
)
async def catnip_db_routine_multi():
    q = Queue(connection=Redis('redis', 6379), default_timeout=3600)
    q.enqueue('utility.db_routine_multi.worker_run_catnip_multi')


@router.post(
    "/catnip/check_rvca_alive",
    dependencies=[Depends(login_token_verification)],
    responses={400: {"description": "Bad Request"}},
    summary='Catnip check_rvca_alive',
    description='Catnip check_rvca_alive'
)
async def catnip_check_rvca_alive():
    q = Queue(connection=Redis('redis', 6379), default_timeout=3600)
    q.enqueue('utility.check_rvca_alive.worker_run_check_rvca_alive')


@router.get(
    "/health",
    dependencies=[Depends(login_token_verification)],
    tags=["util"],
    summary='提供給 monitor 確認服務是否在線的 API',
    description='提供給 monitor 確認服務是否在線的 API, 只會回傳 {"status": "OK"}'
)
async def health_check():
    return {"status": "OK"}
