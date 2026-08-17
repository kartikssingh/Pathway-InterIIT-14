"""Error types and the handlers that render them.

Every failure now leaves the API in the same JSON shape:

```json
{"error": {"code": "not_found", "message": "User 42 was not found", "details": {...}},
 "request_id": "a1b2c3d4"}
```

Previously a validation failure returned FastAPI's ``{"detail": [...]}``, a
business error returned ``{"detail": "string"}`` and an unhandled exception
returned an HTML stack trace in debug mode — three shapes the frontend had to
guess between, which is why ``lib/api.ts`` grew three different error parsers.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

# Starlette's HTTPException, not FastAPI's. FastAPI's subclasses it, so
# registering the base class catches both — including the 404 and 405 the router
# raises for an unmatched path, which a FastAPI-only handler misses and which
# therefore came back in Starlette's `{"detail": "Not Found"}` shape.
from starlette.exceptions import HTTPException

from app.core.logging import get_logger, request_id_var

__all__ = [
    "APIError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "UpstreamError",
    "register_exception_handlers",
    "error_response",
]

log = get_logger("api.errors")


class APIError(Exception):
    """Base class for errors that map cleanly onto an HTTP response."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(APIError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(APIError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationError(APIError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_failed"


class AuthenticationError(APIError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthenticated"


class AuthorizationError(APIError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class UpstreamError(APIError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "upstream_unavailable"


def _request_id(request: Request | None = None) -> str:
    """Prefer the context variable; fall back to request.state for 500s."""
    current = request_id_var.get()
    if current and current != "-":
        return current
    return getattr(getattr(request, "state", None), "request_id", "-")


def error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    request: Request | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "error": {"code": code, "message": message, "details": details or {}},
            "request_id": _request_id(request),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api_error(request: Request, exc: APIError) -> JSONResponse:
        return error_response(
            exc.status_code, exc.code, exc.message, details=exc.details, request=request
        )

    @app.exception_handler(HTTPException)
    async def _http_error(request: Request, exc: HTTPException) -> JSONResponse:
        codes = {
            400: "bad_request",
            401: "unauthenticated",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            409: "conflict",
            429: "rate_limited",
        }
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        details = {} if isinstance(exc.detail, str) else {"detail": exc.detail}
        return error_response(
            exc.status_code,
            codes.get(exc.status_code, "http_error"),
            detail,
            details=details,
            headers=getattr(exc, "headers", None),
            request=request,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {
                "field": ".".join(str(part) for part in error.get("loc", ())[1:]) or "body",
                "message": error.get("msg", "invalid"),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_failed",
            "The request body or query parameters are invalid.",
            details={"fields": fields},
            request=request,
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        log.warning("Database constraint violated", extra={"error": str(exc.orig)[:300]})
        return error_response(
            status.HTTP_409_CONFLICT,
            "conflict",
            "The request conflicts with existing data (duplicate key or violated constraint).",
            request=request,
        )

    @app.exception_handler(OperationalError)
    async def _operational_error(request: Request, exc: OperationalError) -> JSONResponse:
        log.error("Database unavailable", extra={"error": str(exc.orig)[:300]})
        return error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "database_unavailable",
            "The database is not reachable. Try again shortly.",
            request=request,
        )

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        log.exception("Unhandled database error")
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "database_error",
            "A database error occurred.",
            request=request,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled exception")
        from app.core.config import get_settings

        message = (
            f"{type(exc).__name__}: {exc}"
            if get_settings().debug
            else "An unexpected error occurred."
        )
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", message, request=request
        )
