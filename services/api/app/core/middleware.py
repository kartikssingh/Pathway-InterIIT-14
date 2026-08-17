"""Cross-cutting HTTP middleware: request ids, access logging, rate limiting, headers."""

from __future__ import annotations

import time
import uuid
from collections import deque
from threading import Lock

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings
from app.core.errors import error_response
from app.core.logging import get_logger, request_id_var

__all__ = ["register_middleware", "RateLimiter"]

log = get_logger("api.http")

#: Endpoints excluded from rate limiting and access logging noise.
_QUIET_PATHS = frozenset({"/health", "/health/live", "/health/ready", "/metrics"})


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, log the outcome and expose the duration."""

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming or uuid.uuid4().hex[:12]
        token = request_id_var.set(request_id)
        # Also on request.state: an unhandled exception is rendered by Starlette's
        # outermost middleware, by which point the context variable has already
        # been reset — so a 500 would otherwise be the one response with no id.
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            request_id_var.reset(token)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.1f}"

        if request.url.path not in _QUIET_PATHS:
            level = log.warning if response.status_code >= 500 else log.info
            level(
                "%s %s -> %s",
                request.method,
                request.url.path,
                response.status_code,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client": request.client.host if request.client else "unknown",
                },
            )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline hardening headers on every response."""

    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in self.HEADERS.items():
            response.headers.setdefault(header, value)
        return response


class RateLimiter:
    """Fixed-cost sliding-window limiter, keyed by client address.

    In-process and therefore per-worker: it is a guard against a runaway client
    or an accidental loop, not a distributed quota. Set ``REDIS_ENABLED`` and put
    a real limiter in front for that.
    """

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        if self.per_minute <= 0:
            return True, 0
        now = time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.per_minute:
                return False, int(60 - (now - bucket[0])) + 1
            bucket.append(now)
            # Keep the table from growing without bound on a long-lived process.
            if len(self._hits) > 10_000:
                for stale_key in [k for k, v in self._hits.items() if not v][:5_000]:
                    self._hits.pop(stale_key, None)
            return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: RateLimiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _QUIET_PATHS:
            return await call_next(request)

        forwarded = request.headers.get("X-Forwarded-For")
        client = (
            forwarded.split(",")[0].strip()
            if forwarded
            else (request.client.host if request.client else "unknown")
        )
        allowed, retry_after = self.limiter.allow(client)
        if not allowed:
            log.warning("Rate limit exceeded", extra={"client": client, "path": request.url.path})
            return error_response(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "rate_limited",
                f"Too many requests. Retry in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)


def register_middleware(app: FastAPI, settings: Settings) -> None:
    """Order matters: the last one registered is the outermost."""
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(RateLimitMiddleware, limiter=RateLimiter(settings.rate_limit_per_minute))
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        # `allow_origins=["*"]` with `allow_credentials=True` is rejected by every
        # browser; the old config had exactly that combination.
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Response-Time-ms"],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware)
