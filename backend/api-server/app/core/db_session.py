# -*- coding: utf-8 -*-

"""
Generate database session.

History:
2021/08/09 Created by Patrick
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.core_config import settings
from logging import config as logger_config
from logging import getLogger
from traceback import format_exc
from sqlalchemy.orm import Session

logger_config.dictConfig(settings.LOGGER_CONF)
logger = getLogger(__name__)

engine = create_engine(settings.DB_URL)


def get_db_session() -> Generator[Session, None, None]:
    """
    Return database session.

    This is a wrapper of sessionmaker.
    It is convenience to execute sql statement, if that is necessary.
    For db health-checking example:
        db = get_db_session()
        res = db.execute('select 1')
        # response 1 from db means that the db is working well
        res.fetchall()
        res.close()
    """
    make_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = make_session()
    try:
        yield db
    except Exception:
        logger.error(format_exc())
        db.rollback()
    finally:
        db.close()
