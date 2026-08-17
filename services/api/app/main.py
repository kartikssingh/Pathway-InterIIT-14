"""FastAPI application factory.

What changed:

* ``@app.on_event("startup")`` (deprecated) is replaced by a lifespan handler
  that also verifies the database before the service reports ready;
* ``Base.metadata.create_all()`` no longer runs on every boot — the schema is
  owned by ``infra/postgres`` and creating it from the ORM silently produced a
  *different* schema (no CHECK constraints, no triggers, no partial indexes)
  than the one the pipeline writes to. Set ``AUTO_CREATE_TABLES=true`` to opt in
  for local throwaway databases;
* ``allow_origins=["*"]`` with ``allow_credentials=True`` — a combination every
  browser rejects — is replaced by a configured origin list;
* a Redis client was constructed at import from unset environment variables and
  never used; the cache is now lazy and optional;
* errors, request ids, rate limiting, security headers, gzip and health probes
  are wired in here rather than being absent.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure, get_logger
from app.core.middleware import register_middleware

# Importing the models registers them on Base.metadata.
from app.models import (  # noqa: F401
    admin,
    alert,
    audit_log,
    system_health,
    system_metrics,
    toxicity_history,
    transaction,
    user,
    user_sanction_match,
)
from app.routes import (
    auth_routes,
    compliance_routes,
    dashboard_routes,
    export_routes,
    health_routes,
    superadmin_routes,
    transaction_routes,
    user_routes,
)

DESCRIPTION = """
Compliance and fraud-detection API backing the FraudGuard console.

* **Users** — KYC records, risk scores, blacklisting
* **Transactions** — the ledger and its fraud flags
* **Compliance** — alerts raised by the streaming pipeline
* **Dashboard** — aggregates for the operator console
* **Superadmin** — audit logs, system metrics and health

Every error shares one shape:
`{"error": {"code", "message", "details"}, "request_id"}`.
Every response carries `X-Request-ID`; send your own to correlate across services.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log = get_logger("api")

    for warning in settings.warnings:
        log.warning(warning)

    if os.environ.get("AUTO_CREATE_TABLES", "").lower() in {"1", "true", "yes"}:
        from app.db import Base, get_engine

        log.warning(
            "AUTO_CREATE_TABLES is on — creating tables from the ORM. This produces a "
            "schema without the CHECK constraints and triggers in infra/postgres."
        )
        Base.metadata.create_all(bind=get_engine())

    from app.db import check_connection

    healthy, detail = check_connection()
    if healthy:
        log.info("Database reachable", extra={"detail": detail})
    else:
        # Start anyway so /health/ready can explain the problem instead of the
        # container crash-looping with no diagnostics.
        log.error("Database unreachable at start-up", extra={"detail": detail})

    log.info(
        "API ready",
        extra={
            "env": settings.env,
            "version": settings.api_version,
            "cors_origins": ",".join(settings.cors_origins),
        },
    )
    yield

    from app.db import get_engine

    get_engine().dispose()
    log.info("API shut down")


def create_app() -> FastAPI:
    settings = get_settings()
    configure(settings.log_level, json_output=settings.log_json)

    app = FastAPI(
        title=settings.api_title,
        description=DESCRIPTION,
        version=settings.api_version,
        root_path=settings.root_path,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "FraudGuard", "url": "https://pathway.com"},
    )

    register_middleware(app, settings)
    register_exception_handlers(app)

    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(user_routes.router)
    app.include_router(user_routes.users_router)  # plural alias used by the frontend
    app.include_router(transaction_routes.router)
    app.include_router(dashboard_routes.router)
    app.include_router(compliance_routes.router)
    app.include_router(export_routes.router)
    app.include_router(superadmin_routes.router)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app


app = create_app()
