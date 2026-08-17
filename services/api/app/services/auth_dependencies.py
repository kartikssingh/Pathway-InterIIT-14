"""FastAPI dependencies for authentication and authorisation.

Changes:

* the ``tokenUrl`` advertised to Swagger was ``/api/auth/login`` while the router
  is mounted at that prefix — correct, but the value is derived from one constant
  now so the two cannot drift;
* role checks compared against string literals scattered across two functions;
  the roles live in one tuple;
* ``get_client_ip`` trusted ``X-Forwarded-For`` unconditionally, so any client
  could spoof the address written into the audit log. It only trusts the header
  when ``TRUST_PROXY_HEADERS`` is enabled.
"""

from __future__ import annotations

import os

from fastapi import Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, AuthorizationError
from app.core.logging import bind_request
from app.db import get_db
from app.models.admin import Admin
from app.services.auth_service import AuthService

__all__ = [
    "LOGIN_URL",
    "oauth2_scheme",
    "get_current_admin",
    "get_current_active_admin",
    "require_admin",
    "require_superadmin",
    "get_client_ip",
    "get_user_agent",
]

LOGIN_URL = "/api/auth/login"

ADMIN_ROLES = ("admin", "superadmin")
SUPERADMIN_ROLE = "superadmin"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=LOGIN_URL)

_UNAUTHENTICATED_HEADERS = {"WWW-Authenticate": "Bearer"}


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    """Resolve the bearer token to an admin row."""
    token_data = AuthService.verify_token(token)
    if token_data is None or not token_data.username:
        raise AuthenticationError(
            "Could not validate credentials.", details=_UNAUTHENTICATED_HEADERS
        )

    admin = db.query(Admin).filter(Admin.username == token_data.username).first()
    if admin is None:
        # A valid signature for an account that no longer exists.
        raise AuthenticationError(
            "Could not validate credentials.", details=_UNAUTHENTICATED_HEADERS
        )

    bind_request(admin_id=admin.id, admin_role=admin.role)
    return admin


async def get_current_active_admin(
    current_admin: Admin = Depends(get_current_admin),
) -> Admin:
    return current_admin


async def require_admin(current_admin: Admin = Depends(get_current_active_admin)) -> Admin:
    """Any administrator (``admin`` or ``superadmin``)."""
    if current_admin.role not in ADMIN_ROLES:
        raise AuthorizationError("Administrator privileges are required for this action.")
    return current_admin


async def require_superadmin(current_admin: Admin = Depends(get_current_active_admin)) -> Admin:
    """Superadministrators only."""
    if current_admin.role != SUPERADMIN_ROLE:
        raise AuthorizationError("Superadministrator privileges are required for this action.")
    return current_admin


def _trust_proxy_headers() -> bool:
    return os.environ.get("TRUST_PROXY_HEADERS", "").lower() in {"1", "true", "yes"}


def get_client_ip(request: Request | None) -> str:
    """Client address for the audit log.

    ``X-Forwarded-For`` is only honoured behind a proxy you control
    (``TRUST_PROXY_HEADERS=true``); otherwise any caller could forge the address
    recorded against their actions.
    """
    if request is None:
        return "unknown"
    if _trust_proxy_headers():
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request | None) -> str:
    if request is None:
        return "unknown"
    return request.headers.get("User-Agent", "unknown")[:512]


# Kept so callers that build their own 401 keep the right status code.
UNAUTHORIZED_STATUS = status.HTTP_401_UNAUTHORIZED
