"""SQLAlchemy engine, session factory and the request-scoped session dependency.

Changes from the original:

* the connection URL came from ``os.environ["DATABASE_URL"]`` evaluated at import,
  so a missing variable was a ``KeyError`` during module import with no context.
  It now comes from validated settings and can be assembled from the
  ``POSTGRES_*`` variables the rest of the stack already uses.
* ``get_db`` only closed the session; an exception left the transaction open
  until the connection was recycled, and the next request on that connection
  failed with ``InFailedSqlTransaction``. It now rolls back explicitly.
* the engine is created lazily so importing ``app.db`` (which every model does)
  no longer opens sockets — that is what made the test suite require a live
  database just to import a schema.
"""

from __future__ import annotations

import threading
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import get_settings
from app.core.logging import get_logger

__all__ = ["Base", "engine", "SessionLocal", "get_db", "session_scope", "check_connection"]

log = get_logger("api.db")

Base = declarative_base()

_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker | None = None
_LOCK = threading.Lock()


def _build_engine() -> Engine:
    settings = get_settings().database
    created = create_engine(
        settings.url,
        poolclass=QueuePool,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        pool_recycle=settings.pool_recycle,
        pool_pre_ping=True,
        echo=settings.echo,
        connect_args={
            "options": f"-c statement_timeout={settings.statement_timeout_ms}",
            "application_name": "fraudguard-api",
        },
        future=True,
    )
    log.info(
        "Database engine created",
        extra={"pool_size": settings.pool_size, "max_overflow": settings.max_overflow},
    )
    return created


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = _build_engine()
    return _ENGINE


def get_session_factory() -> sessionmaker:
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        with _LOCK:
            if _SESSION_FACTORY is None:
                _SESSION_FACTORY = sessionmaker(
                    autocommit=False, autoflush=False, bind=get_engine(), expire_on_commit=False
                )
    return _SESSION_FACTORY


class _LazyProxy:
    """Attribute access forwards to the real object, created on first use.

    Keeps ``from app.db import engine, SessionLocal`` working for the existing
    modules while removing the import-time connection.
    """

    def __init__(self, factory):
        self._factory = factory

    def __getattr__(self, name):
        return getattr(self._factory(), name)

    def __call__(self, *args, **kwargs):
        return self._factory()(*args, **kwargs)


engine = _LazyProxy(get_engine)
SessionLocal = _LazyProxy(get_session_factory)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, rolled back on failure."""
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class session_scope:
    """Context manager for scripts and background work.

    >>> with session_scope() as db:
    ...     db.add(row)
    """

    def __enter__(self) -> Session:
        self.session = get_session_factory()()
        return self.session

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()
        return False


def check_connection() -> tuple[bool, str]:
    """Readiness probe: ``(healthy, detail)``."""
    try:
        with get_engine().connect() as connection:
            version = connection.execute(text("SELECT version()")).scalar_one()
    except Exception as exc:
        return False, str(exc)[:200]
    return True, str(version).split(",")[0]
