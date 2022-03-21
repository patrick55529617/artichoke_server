"""
Definitions for User related CRUD operations.

History:
2021/09/29 Created by Patrick
"""

from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas.user import UserInfo, NewUserInfo
from app.api.api_v1.endpoints.utils import token_verification
from app.api.api_v1.endpoints.utils.exceptions import ArtichokeException
from app.core.core_config import settings
from logging import config as logger_config
from logging import getLogger
from sqlalchemy.exc import IntegrityError

logger_config.dictConfig(settings.LOGGER_CONF)
logger = getLogger(__name__)


def get_user_info_by_id(db: Session, user_id: str) -> UserInfo:
    sql_stmt = f"SELECT user_id, department, token, last_use_time FROM user_info WHERE user_id = '{user_id}'"
    exe = db.execute(sql_stmt)
    result = exe.fetchone()
    if not result:
        logger.error(f"User {user_id} Not Found")
        raise ArtichokeException("User Not Found")
    user_id, department, token, last_use_time = result
    return UserInfo(user_id=user_id, department=department, token=token, last_use_time=last_use_time)


def add_new_user(db: Session, new_user: NewUserInfo) -> UserInfo:
    user_data = {"user_id": new_user.user_id}
    token = token_verification.create_access_token(user_data)
    last_use_time = datetime.now()
    values = [new_user.user_id, new_user.department, token, str(last_use_time)]
    sql_stmt = f"INSERT INTO user_info VALUES {tuple(values)}"
    try:
        db.execute(sql_stmt)
        db.commit()
        return UserInfo(
            user_id=new_user.user_id,
            department=new_user.department,
            token=token,
            last_use_time=last_use_time
        )
    except IntegrityError:
        logger.error(f"User {new_user.user_id} also exists.")
        raise ArtichokeException("User also exists.")


def get_user_token_by_id(db: Session, user_id: str) -> str:
    sql_stmt = f"SELECT token FROM user_info WHERE user_id = '{user_id}'"
    exe = db.execute(sql_stmt)
    result = exe.fetchone()
    if not result:
        logger.error(f"User {user_id} Not Found")
        raise ArtichokeException("User Not Found")
    token = result[0]
    return token


def refresh_token_proc(db: Session, user_id: str, old_token: str) -> bool:
    sql_stmt = f"SELECT department FROM user_info WHERE user_id = '{user_id}' AND token = '{old_token}'"
    exe = db.execute(sql_stmt)
    result = exe.fetchone()
    if not result:
        logger.error(f"User {user_id} and token not correct.")
        raise ArtichokeException("User and token not correct.")
    new_token = token_verification.create_access_token({"user_id": user_id})
    sql_stmt = f"UPDATE user_info SET token = '{new_token}' WHERE user_id = '{user_id}'"
    db.execute(sql_stmt)
    db.commit()
    return new_token
