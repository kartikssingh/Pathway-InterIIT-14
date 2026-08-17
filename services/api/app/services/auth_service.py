"""Authentication, authorisation and audit logging.

Cryptography now lives in :mod:`app.core.security`; this module is about the
business rules around it.

Fixes:

* ``authenticate_admin`` returned early when the username was unknown, so a
  wrong username answered measurably faster than a wrong password — a username
  oracle. It now always performs a hash comparison.
* the module-level ``SECRET_KEY`` fell back to a placeholder that was committed
  to the repository; it comes from validated settings.
* ``create_audit_log`` committed on every call with no error handling, so a
  failure while recording an action rolled back the action itself. Audit writes
  are now isolated: the action succeeds and the failure is logged loudly.
* ``get_audit_logs`` ran ``query.count()`` *and* fetched every joined admin row
  per log; the admin fields are selected in the same query now.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.schemas.auth import AdminRole, TokenData

__all__ = ["AuthService", "ACCESS_TOKEN_EXPIRE_MINUTES"]

log = get_logger("api.auth")

#: Kept as a module attribute because the routes import it directly.
ACCESS_TOKEN_EXPIRE_MINUTES = get_settings().security.access_token_expire_minutes

#: Hash of an unusable password, compared against when the username is unknown so
#: the response time does not reveal whether the account exists.
_DUMMY_HASH = "$2b$12$0000000000000000000000000000000000000000000000000000"


class AuthService:
    """Static helpers for the auth routes."""

    # -- passwords --------------------------------------------------------- #

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return hash_password(password)

    # -- authentication ---------------------------------------------------- #

    @staticmethod
    def authenticate_admin(db: Session, username: str, password: str) -> Optional[Admin]:
        """Return the admin when the credentials are valid, else ``None``."""
        admin = db.query(Admin).filter(Admin.username == username).first()
        # Always hash, so an unknown username costs the same as a wrong password.
        valid = verify_password(password, admin.hashed_password if admin else _DUMMY_HASH)
        if not admin or not valid:
            log.info("Authentication failed", extra={"username": username[:64]})
            return None
        return admin

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Issue an access token.

        The ``data`` dict shape is kept for the existing call sites.
        """
        return create_access_token(
            subject=str(data.get("sub", "")),
            role=str(data.get("role", "admin")),
            expires_delta=expires_delta,
        )

    @staticmethod
    def create_refresh_token(username: str, role: str) -> str:
        return create_refresh_token(username, role)

    @staticmethod
    def verify_token(token: str, *, expected_type: str = "access") -> Optional[TokenData]:
        payload = decode_token(token, expected_type=expected_type)
        if payload is None:
            return None
        try:
            role = AdminRole(payload.role)
        except ValueError:
            log.warning("Token carries an unknown role", extra={"role": payload.role})
            return None
        return TokenData(username=payload.subject, role=role)

    @staticmethod
    def update_last_login(db: Session, admin_id: int) -> None:
        try:
            db.query(Admin).filter(Admin.id == admin_id).update(
                {Admin.last_login_at: datetime.now(timezone.utc)}
            )
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            log.warning("Could not record the login time", extra={"error": str(exc)[:200]})

    # -- audit ------------------------------------------------------------- #

    @staticmethod
    def create_audit_log(
        db: Session,
        admin_id: int,
        action_type: str,
        action_description: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        target_identifier: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[AuditLog]:
        """Record an admin action.

        ``user_agent`` is accepted for call-site compatibility but not stored —
        there is no such column in the schema.

        A failure here is logged and swallowed: losing the audit record is bad,
        but rolling back the action the operator just performed is worse, and the
        loud log line is what an operator can act on.
        """
        entry = AuditLog(
            admin_id=admin_id,
            action_type=action_type,
            action_description=action_description,
            target_type=target_type,
            target_id=target_id,
            target_identifier=target_identifier,
            action_metadata=metadata,
            ip_address=ip_address,
        )
        try:
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry
        except SQLAlchemyError as exc:
            db.rollback()
            log.error(
                "AUDIT WRITE FAILED — action performed but not recorded",
                extra={
                    "admin_id": admin_id,
                    "action_type": action_type,
                    "target": f"{target_type}:{target_id}",
                    "error": str(exc)[:300],
                },
            )
            return None

    @staticmethod
    def get_audit_logs(
        db: Session,
        admin_id: Optional[int] = None,
        action_type: Optional[str] = None,
        target_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Filtered, paginated audit log with the acting admin joined in."""
        query = db.query(AuditLog).options(joinedload(AuditLog.admin))

        if admin_id:
            query = query.filter(AuditLog.admin_id == admin_id)
        if action_type:
            query = query.filter(AuditLog.action_type == action_type)
        if target_type:
            query = query.filter(AuditLog.target_type == target_type)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        total = query.order_by(None).count()
        rows = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": [
                {
                    "id": row.id,
                    "admin_id": row.admin_id,
                    "admin_username": row.admin.username if row.admin else None,
                    "admin_email": row.admin.email if row.admin else None,
                    "action_type": row.action_type,
                    "action_description": row.action_description,
                    "target_type": row.target_type,
                    "target_id": row.target_id,
                    "target_identifier": row.target_identifier,
                    "metadata": row.action_metadata,
                    "ip_address": row.ip_address,
                    "created_at": row.created_at,
                }
                for row in rows
            ],
        }

    # -- administration ---------------------------------------------------- #

    @staticmethod
    def create_admin(
        db: Session,
        username: str,
        email: str,
        password: str,
        role: AdminRole = AdminRole.ADMIN,
    ) -> Admin:
        admin = Admin(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=role.value if isinstance(role, AdminRole) else str(role),
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        log.info("Admin created", extra={"username": username, "role": admin.role})
        return admin
