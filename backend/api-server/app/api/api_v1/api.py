# -*- coding: utf-8 -*-

"""
Definition of routers on artichoke api service.

Description:
Included routers should be defined in here.

History:
2021/08/09 Created by Patrick
"""

from fastapi import APIRouter
from app.api.api_v1.endpoints import site, sniffer, customer_count, utility, user

api_router = APIRouter()
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(site.router, prefix="/site", tags=["site"])
api_router.include_router(sniffer.router, prefix="/sniffer", tags=["sniffer"])
api_router.include_router(customer_count.router, prefix="/count", tags=["count"])
api_router.include_router(utility.router, prefix="/util", tags=["util"])
