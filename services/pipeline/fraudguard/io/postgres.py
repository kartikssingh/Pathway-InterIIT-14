"""Pooled PostgreSQL access for the pipeline.

Previously each module opened one global ``psycopg2`` connection at *import*
time and reused a single cursor from inside Pathway UDFs.  That is unsafe
(cursors are not thread-safe, Pathway runs UDFs on a worker pool) and a single
network hiccup poisoned the connection for the lifetime of the process.

This module provides a lazily-created :class:`psycopg2.pool.ThreadedConnectionPool`
plus context managers that always return the connection and roll back on error.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor

from fraudguard.logging import get_logger

__all__ = ["connection", "cursor", "fetch_one", "fetch_all", "execute", "close_pool"]

log = get_logger("fraudguard.postgres")

_POOL: pg_pool.ThreadedConnectionPool | None = None
_POOL_LOCK = threading.Lock()


def _get_pool() -> pg_pool.ThreadedConnectionPool:
    global _POOL
    if _POOL is None:
        with _POOL_LOCK:
            if _POOL is None:
                from fraudguard.config import get_settings

                pg = get_settings().postgres
                _POOL = pg_pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=int(_max_connections()),
                    host=pg.host,
                    port=pg.port,
                    dbname=pg.dbname,
                    user=pg.user,
                    password=pg.password,
                    connect_timeout=10,
                    application_name="fraudguard-pipeline",
                )
                log.info("Postgres pool ready", extra={"dsn_host": pg.host, "db": pg.dbname})
    return _POOL


def _max_connections() -> int:
    import os

    try:
        return max(2, int(os.environ.get("POSTGRES_POOL_SIZE", "10")))
    except ValueError:
        return 10


@contextmanager
def connection() -> Iterator[psycopg2.extensions.connection]:
    """Borrow a connection; commit on success, roll back on failure."""
    pool_ = _get_pool()
    conn = pool_.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except psycopg2.Error:  # connection already dead
            pass
        raise
    finally:
        pool_.putconn(conn)


@contextmanager
def cursor(dict_rows: bool = False) -> Iterator[psycopg2.extensions.cursor]:
    """Borrow a connection and hand back a fresh cursor."""
    with connection() as conn:
        factory = RealDictCursor if dict_rows else None
        with conn.cursor(cursor_factory=factory) as cur:
            yield cur


def fetch_one(sql: str, params: Sequence[Any] = ()) -> tuple[Any, ...] | None:
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def fetch_all(sql: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
    with cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def execute(sql: str, params: Sequence[Any] = ()) -> int:
    """Run a statement and return the affected row count."""
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def close_pool() -> None:
    """Close every pooled connection (call on shutdown)."""
    global _POOL
    with _POOL_LOCK:
        if _POOL is not None:
            _POOL.closeall()
            _POOL = None
            log.info("Postgres pool closed")
