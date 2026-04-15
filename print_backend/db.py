"""SQLAlchemy engine and session factory."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def get_database_url() -> str | None:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    return url or None


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine, _SessionLocal
    url = get_database_url()
    if not url:
        return None
    if _engine is None:
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_session_factory():
    eng = get_engine()
    if eng is None:
        return None
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return _SessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for request-scoped DB session."""
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("DATABASE_URL is not set")
    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> bool:
    """Create tables if they do not exist. Returns False if no DATABASE_URL."""
    from print_backend.models import User, PrintJob  # noqa: F401

    eng = get_engine()
    if eng is None:
        return False
    Base.metadata.create_all(bind=eng)
    return True


def reset_engine() -> None:
    """Dispose engine and clear session factory (tests or DATABASE_URL change)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
