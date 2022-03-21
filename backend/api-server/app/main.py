# -*- coding: utf-8 -*-

"""
Definition of artichoke api service.

Description:
The main file of artichoke api service,
included routers should be defined in here.
It is developed by FastAPI framework.

History:
2021/08/09 Created by Patrick
2021/10/15 Add Descriptions by Patrick
"""
from typing import Optional
from fastapi import FastAPI
from app.api.api_v1.api import api_router
from app.core.core_config import settings


description = """
Artichoke API Server helps you do awesome stuff. 🚀

### User

用來新增 api user / 取得最新 token / 刷新 token

### Site

提供有關門店設定，查詢，新增門店的 API

### Sniffer

提供有關門店內天線設定，查詢，新增或更換的 API

### Customer Count

即時人流 / 歷史人流計算

### Utility

舊版本的 script 整合到 worker 內，可使用 API Server 驅動。
"""


app = FastAPI(
    root_path=settings.API_ROOT_PATH,
    description=description,
    title="Artichoke API Server",
    contact={
        "name": "Artichoke Maintainer",
        "email": "patrick.hu@testritegroup.com"
    },
    version=settings.API_VERSION
)

app.include_router(
    api_router,
    prefix=settings.API_V1_STR,
)
