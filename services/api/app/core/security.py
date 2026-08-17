"""Password hashing and JWT issuing/verification.

Lifted out of ``AuthService`` so the cryptography lives in one auditable place
and the service layer is about business rules.

Behaviour changes:

* the signing key comes from validated settings, so the service can no longer
  start with the placeholder key that was committed as a default;
* ``datetime.utcnow()`` (naive, deprecated in 3.12) is replaced with timezone-aware
  UTC — the old tokens' ``exp`` was compared against a naive clock;
* tokens carry ``iat``, ``jti`` and ``typ``, so refresh tokens cannot be replayed
  as access tokens and individual tokens can be revoked by id;
* ``verify_password`` no longer raises when a stored hash is malformed (a
  ``ValueError`` from bcrypt used to surface as a 500 instead of a 401).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.logging import get_logger

__all__ = [
    "TokenPayload",
    "hash_password",
    "verify_password",
    "needs_rehash",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
]

log = get_logger("api.security")

ACCESS = "access"
REFRESH = "refresh"

#: bcrypt silently truncates beyond 72 bytes; reject rather than truncate.
MAX_PASSWORD_BYTES = 72


@dataclass(frozen=True)
class TokenPayload:
    subject: str
    role: str
    token_type: str
    expires_at: datetime
    token_id: str
    raw: dict[str, Any]


# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes; bcrypt truncates beyond that."
        )
    rounds = get_settings().security.bcrypt_rounds
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds)).decode("utf-8")


def verify_password(plain: str, hashed: str | None) -> bool:
    """Constant-time verification that never raises on malformed input."""
    if not hashed:
        # Still spend the time so a missing account is not distinguishable by timing.
        bcrypt.checkpw(b"placeholder", bcrypt.hashpw(b"placeholder", bcrypt.gensalt(4)))
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:MAX_PASSWORD_BYTES], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        log.warning("Stored password hash is malformed")
        return False


def needs_rehash(hashed: str) -> bool:
    """True when a stored hash uses fewer rounds than the current policy."""
    try:
        rounds = int(hashed.split("$")[2])
    except (IndexError, ValueError):
        return True
    return rounds < get_settings().security.bcrypt_rounds


# --------------------------------------------------------------------------- #
# Tokens
# --------------------------------------------------------------------------- #


def _create_token(subject: str, role: str, token_type: str, lifetime: timedelta) -> str:
    settings = get_settings().security
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(
    subject: str, role: str, *, expires_delta: timedelta | None = None
) -> str:
    settings = get_settings().security
    lifetime = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    return _create_token(subject, role, ACCESS, lifetime)


def create_refresh_token(subject: str, role: str) -> str:
    settings = get_settings().security
    return _create_token(
        subject, role, REFRESH, timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str, *, expected_type: str = ACCESS) -> TokenPayload | None:
    """Decode and validate a token; ``None`` for anything not usable."""
    settings = get_settings().security
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        log.debug("Token rejected", extra={"reason": str(exc)})
        return None

    subject = claims.get("sub")
    role = claims.get("role")
    if not subject or not role:
        return None

    # Tokens minted before this field existed are treated as access tokens.
    token_type = claims.get("typ", ACCESS)
    if token_type != expected_type:
        log.debug("Token type mismatch", extra={"expected": expected_type, "got": token_type})
        return None

    return TokenPayload(
        subject=str(subject),
        role=str(role),
        token_type=token_type,
        expires_at=datetime.fromtimestamp(claims.get("exp", 0), tz=timezone.utc),
        token_id=str(claims.get("jti", "")),
        raw=claims,
    )
