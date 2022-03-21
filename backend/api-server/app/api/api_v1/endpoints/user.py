# -*- coding: utf-8 -*-

"""
Definition of the user router for the artichoke api service.

Description:
The schemas and routers of User are defined in here.

History:
2021/09/29 Created by Patrick
"""

import datetime
from fastapi import APIRouter, HTTPException, Body, Depends, Header
from sqlalchemy.orm import Session
from app.core.db_session import get_db_session
from app.crud import crud_user
from app.schemas.user import UserInfo, NewUserInfo
from app.core.core_config import settings
from app.api.api_v1.endpoints.utils.exceptions import ArtichokeException
from app.api.api_v1.endpoints.utils.token_verification import login_token_verification

from logging import config as logger_config
from logging import getLogger
logger_config.dictConfig(settings.LOGGER_CONF)
logger = getLogger(__name__)

router: APIRouter = APIRouter()


@router.get(
    "/{user_id}",
    dependencies=[Depends(login_token_verification)],
    tags=["user"],
    responses={400: {"description": "User Not Found"}},
    summary='取得使用者的資訊, 包括 token',
    description='輸入 user_id, 取得使用者的資訊'
)
async def get_user_info(
    user_id: str,
    db: Session = Depends(get_db_session)
) -> UserInfo:
    try:
        user_info = crud_user.get_user_info_by_id(db, user_id)
        return user_info
    except ArtichokeException as e:
        raise HTTPException(status_code=400, detail=e.msg)


@router.post(
    "/register",
    dependencies=[Depends(login_token_verification)],
    responses={400: {"description": "User Not Found"}},
    summary='新增 api server 的使用者',
    description='輸入 user_id 及部門資訊，進行註冊並返回 token 供使用者使用'
)
async def add_new_api_user(
    db: Session = Depends(get_db_session),
    new_user: NewUserInfo = Body(
        ...,
        example={
            "user_id": "HI0008",
            "department": "EDT",
        }
    )
) -> UserInfo:
    try:
        user_info = crud_user.add_new_user(db, new_user)
        return user_info
    except ArtichokeException as e:
        raise HTTPException(status_code=400, detail=e.msg)


@router.get(
    "/token/{user_id}",
    tags=["user"],
    responses={400: {"description": "User Not Found"}},
    summary='取得使用者 token',
    description='輸入 user_id, 取得使用者的 token'
)
async def get_user_token(
    user_id: str,
    db: Session = Depends(get_db_session)
) -> dict:
    try:
        token = crud_user.get_user_token_by_id(db, user_id)
        return {"token": token}
    except ArtichokeException as e:
        raise HTTPException(status_code=400, detail=e.msg)


@router.put(
    "/token/{user_id}",
    tags=["user"],
    responses={400: {"description": "User Not Found"}},
    summary='刷新 token',
    description='輸入 user_id, body 輸入過期的 token, 以得到新的 token'
)
async def refresh_token(
    user_id: str,
    db: Session = Depends(get_db_session),
    token: str = Header(None)
) -> dict:
    try:
        new_token = crud_user.refresh_token_proc(db, user_id, token)
        return {"token": new_token}
    except ArtichokeException as e:
        raise HTTPException(status_code=400, detail=e.msg)
