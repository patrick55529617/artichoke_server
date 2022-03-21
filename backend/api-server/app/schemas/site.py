# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field
import datetime
from enum import Enum
from typing import Optional, Union, List


class Channel(str, Enum):

    TLW = 'TLW'
    HOLA = 'HOLA'
    HOI = 'HOI'
    PETITE = 'PETITE'
    CB = 'CB'
    WMF = 'WMF'


class Region(str, Enum):

    NORTHERN = 'Northern'
    CENTRAL = 'Central'
    SOUTHERN = 'Southern'


class Group(str, Enum):

    NORMAL = '標準店'
    COMMUNITY = '社區店'
    PETITE = 'PETITE'


class SiteInfo(BaseModel):

    site_id: str = Field(
        ...,
        title="site id",
        example="1A01"
    )
    sname: str = Field(
        ...,
        title="site name",
        example="TLW桃園南崁店"
    )
    channel: Channel = Field(
        ...,
        title="channel for all sites",
        example=Channel.TLW
    )
    open_hour: str = Field(
        ...,
        title="Open hour for the site on non-weekend",
        example="10:00:00"
    )
    closed_hour: str = Field(
        ...,
        title="Closed hour for the site on non-weekend",
        example="21:00:00"
    )
    open_hour_wend: str = Field(
        ...,
        title="Open hour for the site on weekend",
        example="10:00:00"
    )
    closed_hour_wend: str = Field(
        ...,
        title="Closed hour for the site on weekend",
        example="21:00:00"
    )
    is_released: bool = Field(
        ...,
        title="If the site is working or not.",
        example=True
    )
    android_rate: float = Field(
        ...,
        title="Android rate for the site",
        example=0.62
    )
    wifi_rate: float = Field(
        ...,
        title="Wifi rate for the site",
        example=0.66
    )
    region: Union[Region, None] = Field(
        ...,
        title="Where the site is located",
        example=Region.NORTHERN
    )
    group: Union[Group, None] = Field(
        ...,
        title="Size of the site",
        example=Group.NORMAL
    )
    alg_version: int = Field(
        ...,
        title="Artichoke algorithm version of the site",
        example=2
    )
    alg_params: Union[dict, None] = Field(
        ...,
        title="Artichoke algorithm parameters of the site",
        example={
            "model_slope": 99.9832,
            "manual_slope": 178.5654,
            "model_intercept": 1101.3628,
            "model_upper_limit": 2805.7401
        }
    )
    tel: Union[str, None] = Field(
        ...,
        title="Telephone for the site",
        example="03-321-1000"
    )
    hostname: Union[str, None] = Field(
        ...,
        title="Hostname for the site",
        example="Nankan"
    )


class SiteInfoWithSniffer(SiteInfo):

    sniffer_ids: Union[List[str], None] = Field(
        ...,
        title="sniffer ids in the site",
        example=['74da38db1f97']
    )
    rssi: Union[List[int], None] = Field(
        ...,
        title="sniffer rssi in the site",
        example=[-98]
    )


class RssiMonitorConfigSite(BaseModel):

    site_id: str = Field(
        ...,
        title="site id",
        example="1G55"
    )
    sname: str = Field(
        ...,
        title="site name",
        example="TLW苓雅三多店"
    )
    android_rate: float = Field(
        ...,
        title="Android rate for the site",
        example=0.35
    )
    wifi_rate: float = Field(
        ...,
        title="Wifi rate for the site",
        example=0.66
    )
    day_from: str = Field(
        ...,
        title="site open date",
        example="2021-10-30"
    )
