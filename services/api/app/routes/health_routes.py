"""Liveness, readiness and build information.

The frontend polls a health endpoint to decide whether to show its "server down"
screen (``useHealthCheck.ts``), but the API had no health endpoint at all — the
frontend was probing ``/`` and treating any 200 as healthy, so it showed a green
light while the database was unreachable.
"""

from __future__ import annotations

import os
import platform
import time
from typing import Any

from fastapi import APIRouter, Response, status

from app.core.cache import is_available as cache_available
from app.core.cache import ping as cache_ping
from app.core.config import get_settings
from app.db import check_connection

router = APIRouter(tags=["Health"])

_STARTED_AT = time.time()


@router.get("/health/live", summary="Liveness — is the process running?")
def live() -> dict[str, Any]:
    return {"status": "alive", "uptime_seconds": round(time.time() - _STARTED_AT, 1)}


@router.get("/health/ready", summary="Readiness — can it serve traffic?")
def ready(response: Response) -> dict[str, Any]:
    db_ok, db_detail = check_connection()
    checks = {
        "database": {"healthy": db_ok, "detail": db_detail},
        "cache": {
            "healthy": True,  # the cache is optional; unavailable is not unhealthy
            "detail": "connected"
            if cache_ping()
            else ("enabled but unreachable" if cache_available() else "disabled"),
        },
    }
    healthy = all(check["healthy"] for check in checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if healthy else "degraded", "checks": checks}


@router.get("/health", summary="Combined health summary")
def health(response: Response) -> dict[str, Any]:
    settings = get_settings()
    payload = ready(response)
    payload.update(
        {
            "service": settings.api_title,
            "version": settings.api_version,
            "environment": settings.env,
            "uptime_seconds": round(time.time() - _STARTED_AT, 1),
        }
    )
    return payload


@router.get("/version", summary="Build and runtime information")
def version() -> dict[str, Any]:
    settings = get_settings()
    return {
        "service": settings.api_title,
        "version": settings.api_version,
        "environment": settings.env,
        "python": platform.python_version(),
        "commit": os.environ.get("GIT_COMMIT", "unknown"),
    }
