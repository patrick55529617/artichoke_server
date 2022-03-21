# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field
import datetime
from enum import Enum
from typing import Optional, Union, List


class DailyReportInput(BaseModel):

    nday: int = Field(
        ...,
        title="calculate how many days",
        example=1
    )
    target_date: Union[str, None] = Field(
        ...,
        title="target date for the request sending missing record, may be None",
        example="2021-08-27"
    )


class MissingRecordInput(BaseModel):

    site_id: Union[str, None] = Field(
        ...,
        title="target site_id for the request missing record, may be None",
        example="1A01"
    )
    target_date: Union[str, None] = Field(
        ...,
        title="target date for the request missing record, may be None",
        example="2021-08-27"
    )
    nday: int = Field(
        ...,
        title="calculate how many days",
        example=1
    )
    rday: int = Field(
        ...,
        title="r days ago to target date. Default is 7 days",
        example=7
    )
    tolerance: int = Field(
        ...,
        title="Max. tolerance time of missing rawdata, with unit minutes",
        example=5
    )
    only_weekly: bool = Field(
        ...,
        title="Only get missing record report in a range.",
        example=False
    )


class EposRoutineInput(BaseModel):

    nday: int = Field(
        ...,
        title="calculate how many days",
        example=1
    )
    target_date: Union[str, None] = Field(
        ...,
        title="target date for the request sending missing record, may be None",
        example="2021-08-27"
    )
    site_id: Union[str, None] = Field(
        ...,
        title="target site_id for the request epos routine, may be None",
        example="1A01"
    )


class AlertWeeklyInput(BaseModel):

    start_time: Union[str, None] = Field(
        ...,
        title="Start timestamp for calculating alert statistic, may be None.",
        example="2021-08-30 08:00:00"
    )
    end_time: Union[str, None] = Field(
        ...,
        title="End timestamp for calculating alert statistic, may be None.",
        example="2021-09-06 08:00:00"
    )


class DbRoutineInput(BaseModel):

    specific_date: str = Field(
        ...,
        title="target date for the request calculating customer count",
        example="2021-09-05"
    )


class DbRoutineInputOneSite(DbRoutineInput):

    site_id: Union[str, None] = Field(
        ...,
        title="target site_id, may be None",
        example="1A01"
    )


class DbBackupInput(BaseModel):

    year: int = Field(
        ...,
        title="year",
        example="2021"
    )
    month: int = Field(
        ...,
        title="month",
        example="12"
    )
