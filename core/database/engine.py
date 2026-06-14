'''
Engine, session factory and schema bootstrap for the SQLite database.

The database file lives at data/rcm.db.
'''

from __future__ import annotations

import contextlib
import typing

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import config
from core.database.models import Base

DB_PATH = config.DATA_DIRECTORY / 'rcm.db'
DB_URL = f'sqlite:///{DB_PATH}'

ENGINE = create_engine(DB_URL, future=True)
SessionLocal = sessionmaker(bind=ENGINE, expire_on_commit=False, future=True)


def init_db() -> None:
    '''Create all tables if they do not already exist.'''
    Base.metadata.create_all(ENGINE)


@contextlib.contextmanager
def session_scope() -> typing.Iterator[Session]:
    '''Transactional session: commits on success, rolls back on error.'''
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
