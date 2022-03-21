# -*- coding: utf-8 -*-

"""
Generate database session.

History:
2021/02/24 Created by Patrick
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from traceback import format_exc


def db_session(db_url: str) -> Generator[Session, None, None]:
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
    engine = create_engine(db_url, pool_pre_ping=True)
    make_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = make_session()
    try:
        yield db
    except Exception:
        logger.error(format_exc())
        db.rollback()
        db.close()
