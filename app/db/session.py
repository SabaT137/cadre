from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base


@lru_cache
def get_app_engine() -> Engine:
    url = get_settings().app_database_url
    if url.startswith("sqlite:///"):
        from pathlib import Path

        Path(url[len("sqlite:///"):]).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


@lru_cache
def _factory() -> sessionmaker:
    return sessionmaker(bind=get_app_engine(), expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(get_app_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    s: Session = _factory()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    with session_scope() as s:
        yield s
