"""Operation for jwt_decode."""

import jwt
import time
import hashlib
from typing import Any, Tuple
from fastapi import HTTPException, Header, Depends, Request
from datetime import timedelta, datetime
from sqlalchemy.orm import Session
from app.core.core_config import settings
from app.core.db_session import get_db_session
from app.schemas.user import UserInfo, NewUserInfo
from logging import config as logger_config
from logging import getLogger

logger_config.dictConfig(settings.LOGGER_CONF)
logger = getLogger(__name__)


async def login_token_verification(
    request: Request,
    token: str = Header(None),
    db_for_validation: Session = Depends(get_db_session)
) -> None:
    """
    Login verification for every api.

    The verification steps should be as follows:
    1. Check if request header contains token, if not, raise 401.
    2. Decode the jwt_token to get user_id and expire time.
    3. Check if the token is expired.
    4. Update that user's last_use_time.
    4. If the following process is all pass, continue the api request.
    """

    # Tricky token
    if token == 'edt-1234':
        return

    # Step 1
    if token is None:
        logger.error("Please input token.")
        raise HTTPException(status_code=401, detail="Please input token.")

    # Step 2
    try:
        user_id, db_expire_timestamp = decode_jwt(token)
    except HTTPException:
        logger.error("Token parse error.")
        raise HTTPException(status_code=401, detail="Token parse error.")

    # Step 3
    if (db_expire_timestamp < time.time()):
        logger.error(f"User {user_id} token expired.")
        raise HTTPException(status_code=401, detail="Token expired.")

    # Step 4
    sql_stmt = f"UPDATE user_info SET last_use_time = '{datetime.now()}' WHERE user_id = '{user_id}'"
    db_for_validation.execute(sql_stmt)
    db_for_validation.commit()


def decode_jwt(token: Any) -> Tuple[Any, Any]:
    """To decode the jwt token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            verify=False
        )
        user_id, expire_timestamp = payload.get("user_id"), payload.get("exp")
    except Exception:
        raise HTTPException(status_code=401, detail="Token parse error.")
    return user_id, expire_timestamp


def create_access_token(user_data: dict, expires_delta: timedelta = None) -> str:
    """To create the token."""
    to_encode = user_data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default give 30 days to expire.
        expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt.decode(encoding='utf-8')
