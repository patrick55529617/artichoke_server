"""Operation for api requests."""

import requests
from app.core.core_config import settings
from app.api.api_v1.endpoints.utils.exceptions import ArtichokeException


def get_frp_status(site_id: str) -> bool:
    auth = (settings.ACCOUNT, settings.PASSWORD)
    resp = requests.get(settings.FRP_URL, auth=auth)
    if resp.status_code != 200:
        raise ArtichokeException("FRP Server Error.")
    resp_json = resp.json()
    if resp_json.get("code") != 0:
        raise ArtichokeException("FRP Server Error.")
    rawdata = resp_json.get("proxies")
    rawdata_input_site = [i for i in rawdata if site_id in i.get("name")]
    if not rawdata_input_site:
        raise ArtichokeException("Site id not found.")
    for r in rawdata_input_site:
        if r.get("status") != 'online':
            return False
    return True
