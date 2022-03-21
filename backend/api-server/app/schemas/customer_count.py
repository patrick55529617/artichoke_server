# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field
import datetime
from enum import Enum
from typing import Optional, Union, List


class HourlyStatistic(BaseModel):

    hour: str = Field(
        ...,
        title="period of the record time",
        example="10:00:00"
    )
    count: int = Field(
        ...,
        title="customer count for the time",
        example=10
    )


class DailyStatistic(BaseModel):

    date: str = Field(
        ...,
        title="period of the record time",
        example="10:00:00"
    )
    count: int = Field(
        ...,
        title="customer count for the time",
        example=10
    )


class CustomerCount(BaseModel):

    site_id: str = Field(
        ...,
        title="site id",
        example="1A01"
    )
    data: List[Union[HourlyStatistic, DailyStatistic]] = Field(
        ...,
        title="customer count of the site, unit may be hour or day",
        example=[
            {
                "hour": "10:00:00",
                "count": 10
            },
            {
                "hour": "11:00:00",
                "count": 20
            }
        ]
    )


class HistoryQuery(BaseModel):

    site_ids: str = Field(
        ...,
        title="site ids, with commas",
        example="1A01,1A02"
    )
    start_dt: str = Field(
        ...,
        title="start date of query period",
        example="2021-08-20"
    )
    end_dt: str = Field(
        ...,
        title="start date of query period",
        example="2021-08-24"
    )
