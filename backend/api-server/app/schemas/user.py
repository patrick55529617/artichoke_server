# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field
import datetime
from enum import Enum
from typing import Optional, Union, List


class NewUserInfo(BaseModel):

    user_id: str = Field(
        ...,
        title="使用者的工號",
        example="HI0008"
    )
    department: str = Field(
        ...,
        title="使用者的部門",
        example="EDT"
    )


class UserInfo(NewUserInfo):

    token: str = Field(
        ...,
        title="登入時使用的 token",
        example="xxxxxx"
    )
    last_use_time: datetime.datetime = Field(
        ...,
        title="最後一次使用 api 的時間",
        example="2021-08-21 00:00:00"
    )
