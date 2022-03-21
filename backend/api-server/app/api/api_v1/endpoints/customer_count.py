# -*- coding: utf-8 -*-

"""
Definition of the customer_count router for the artichoke api service.

Description:
The schemas and routers of customer_count are defined in here.

History:
2021/08/24 Created by Patrick
2021/10/07 Add Token Verification for Each Endpoint by Patrick
"""

from fastapi import APIRouter, HTTPException, Body, Depends
from app.core.db_session import get_db_session
from app.crud import crud_customer_count
from app.core.core_config import settings
from app.schemas.customer_count import CustomerCount, HistoryQuery
from app.api.api_v1.endpoints.utils.exceptions import ArtichokeException
from app.api.api_v1.endpoints.utils.token_verification import login_token_verification
from logging import config as logger_config
from logging import getLogger
from sqlalchemy.orm import Session

logger_config.dictConfig(settings.LOGGER_CONF)
logger = getLogger(__name__)

router: APIRouter = APIRouter()


@router.get(
    "/today/{site_ids}",
    dependencies=[Depends(login_token_verification)],
    tags=["count"],
    responses={400: {"description": "Site Not Found"}},
    summary='計算即時人流數據',
    description='可輸入多個 site_id, 中間以 "," 切開, 會回傳輸入門店的即時人流資訊'
)
async def get_realtime_customer_count_by_site_id(
    site_ids: str,
    db: Session = Depends(get_db_session)
) -> [CustomerCount]:
    """Get realtime customer count by site_ids, with commas for each site_id."""
    #XXX: site_id regex
    realtime_counts = crud_customer_count.get_realtime_report_by_site_id(db, site_ids)
    return realtime_counts


@router.post(
    "/history",
    dependencies=[Depends(login_token_verification)],
    tags=["count"],
    responses={400: {"description": "Site Not Found"}},
    summary='計算歷史人流數據',
    description='可輸入多個 site_id, 中間以 "," 切開, 和欲計算之日期區間, 回傳輸入門店的歷史人流資訊'
)
async def get_history_customer_count_by_site_id(
    db: Session = Depends(get_db_session),
    history_query: HistoryQuery = Body(
        ...,
        example={
            "site_ids": "1A01,1A02,1A03",
            "start_dt": "2021-08-20",
            "end_dt": "2021-08-24"
        }
    )
) -> [CustomerCount]:
    #XXX: site_id regex
    history_counts = crud_customer_count.get_history_report_by_site_ids(db, history_query)
    return history_counts
