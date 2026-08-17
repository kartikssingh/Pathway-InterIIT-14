"""Optional Redis cache.

``main.py`` used to do this at import time::

    redis_client = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), ...)

With the variables unset that constructs a client pointed at ``None`` with a
``None`` port, and nothing in the codebase ever used it. Redis is genuinely
useful for the dashboard aggregates, so it is kept — but optional, lazy, and
with every operation degrading to a miss when it is unavailable.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Callable

from app.core.config import get_settings
from app.core.logging import get_logger

__all__ = ["cache_get", "cache_set", "cached", "invalidate", "is_available", "ping"]

log = get_logger("api.cache")

_CLIENT: Any | None = None
_CHECKED = False
_LOCK = threading.Lock()


def _client() -> Any | None:
    global _CLIENT, _CHECKED
    if _CHECKED:
        return _CLIENT
    with _LOCK:
        if _CHECKED:
            return _CLIENT
        _CHECKED = True
        settings = get_settings().redis
        if not settings.enabled:
            log.info("Redis disabled (set REDIS_ENABLED=true to turn it on)")
            return None
        try:
            import redis

            client = redis.Redis.from_url(
                settings.url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
            )
            client.ping()
            _CLIENT = client
            log.info("Redis connected", extra={"host": settings.host, "db": settings.db})
        except Exception as exc:
            log.warning("Redis unavailable; running without a cache", extra={"error": str(exc)})
            _CLIENT = None
    return _CLIENT


def is_available() -> bool:
    return _client() is not None


def ping() -> bool:
    client = _client()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception:
        return False


def cache_get(key: str) -> Any | None:
    client = _client()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except Exception as exc:
        log.debug("Cache read failed", extra={"key": key, "error": str(exc)})
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set(key: str, value: Any, ttl_seconds: int = 60) -> None:
    client = _client()
    if client is None:
        return
    try:
        client.setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception as exc:
        log.debug("Cache write failed", extra={"key": key, "error": str(exc)})


def invalidate(pattern: str) -> int:
    """Delete keys matching a glob. Returns how many were removed."""
    client = _client()
    if client is None:
        return 0
    removed = 0
    try:
        for key in client.scan_iter(match=pattern, count=500):
            removed += client.delete(key)
    except Exception as exc:
        log.debug("Cache invalidation failed", extra={"pattern": pattern, "error": str(exc)})
    return removed


def cached(key: str, ttl_seconds: int = 60) -> Callable[[Callable[[], Any]], Any]:
    """Read-through helper::

    result = cached("dashboard:summary", 30)(lambda: expensive_query(db))
    """

    def wrapper(producer: Callable[[], Any]) -> Any:
        hit = cache_get(key)
        if hit is not None:
            return hit
        value = producer()
        cache_set(key, value, ttl_seconds)
        return value

    return wrapper
