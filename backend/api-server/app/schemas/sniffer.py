# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field
import datetime
from enum import Enum
from typing import List, Optional, Union


class SnifferInfo(BaseModel):

    site_id: str = Field(
        ...,
        title="site id",
        example="1A01"
    )
    sniffer_id: str = Field(
        ...,
        title="sniffer_ids in the site",
        example='74da38db1f97',
    )
    is_active: bool = Field(
        ...,
        title="is_active flag for each sniffer",
        example=True,
    )
    rssi: int = Field(
        ...,
        title="rssi for each sniffer",
        example=-98,
    )
    machine_area: str = Field(
        ...,
        title="安裝區域",
        example='41號走道',
    )
    machine_location: str = Field(
        ...,
        title="安裝方式",
        example='貨架',
    )
    ip: str = Field(
        ...,
        title="ip address",
        example='10.28.1.231/24',
    )
    dns: str = Field(
        ...,
        title="DNS",
        example='172.17.64.78,172.16.1.26',
    )
    network_type: str = Field(
        ...,
        title="DHCP",
        example='DHCP',
    )
    ups_is_active: bool = Field(
        ...,
        title="If the ups is on.",
        example=True
    )
    wifi_no: str = Field(
        ...,
        title="wifi_no",
        example='48',
    )
    wifi_mac: str = Field(
        ...,
        title="wifi mac",
        example='74da38db2019',
    )
    sniffer_no: str = Field(
        ...,
        title="sniffer_no",
        example='48',
    )
    gateway: str = Field(
        ...,
        title="gateway",
        example='10.28.1.250',
    )


class RssiMonitorConfigSniffer(BaseModel):

    site_id: str = Field(
        ...,
        title="site id",
        example="1G55"
    )
    sniffer_id: str = Field(
        ...,
        title="sniffer_ids in the site",
        example='08beac0f901f',
    )
    rssi_group: str = Field(
        ...,
        title="candidates of rssis",
        example="-62,-64,-68",
    )
