"""Shared HTTP client with retries, backoff and a connection pool.

The original code created a fresh ``requests.Session`` per call (so TLS was
re-negotiated on every lookup) and had no retry policy at all — a single blip
from OpenSanctions produced a permanently null enrichment for that entity.
"""

from __future__ import annotations

import threading
from functools import lru_cache
from typing import Any, Mapping

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from fraudguard.errors import RateLimitedError, UpstreamError
from fraudguard.logging import get_logger

__all__ = ["get_session", "request_json"]

log = get_logger("fraudguard.http")
_LOCK = threading.Lock()


@lru_cache(maxsize=8)
def _build_session(retries: int, pool_size: int) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST", "HEAD"}),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=pool_size, pool_maxsize=pool_size)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "FraudGuard/2.0 (+compliance-pipeline)"})
    return session


def get_session(retries: int | None = None, pool_size: int = 16) -> requests.Session:
    """Return a pooled, retrying session (one per ``retries`` value)."""
    from fraudguard.config import get_settings

    if retries is None:
        retries = get_settings().enrichment.http_retries
    with _LOCK:
        return _build_session(retries, pool_size)


def request_json(
    method: str,
    url: str,
    *,
    service: str,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
    json_body: Any | None = None,
    timeout: int | None = None,
) -> Any:
    """Perform a request and return decoded JSON, mapping failures to our errors."""
    from fraudguard.config import get_settings

    settings = get_settings().enrichment
    timeout = timeout or settings.http_timeout_s
    session = get_session()

    try:
        response = session.request(
            method.upper(),
            url,
            headers=dict(headers or {}),
            params=dict(params or {}),
            json=json_body,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise UpstreamError(service, f"network error: {exc}") from exc

    if response.status_code == 429:
        raise RateLimitedError(service, "quota exceeded", status_code=429)
    if response.status_code >= 400:
        raise UpstreamError(
            service,
            f"HTTP {response.status_code}: {response.text[:200]}",
            status_code=response.status_code,
        )

    try:
        return response.json()
    except ValueError as exc:
        raise UpstreamError(service, f"response was not JSON: {response.text[:200]}") from exc
