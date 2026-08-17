"""Application settings.

Configuration used to be read wherever it was needed: ``os.environ["DATABASE_URL"]``
in ``db.py``, ``os.getenv("SECRET_KEY", "your-secret-key-change-this-...")`` in
``auth_service.py``, ``os.getenv("REDIS_HOST")`` at module scope in ``main.py``.
The result was a service that started happily with a publicly-known signing key
and only discovered a missing database URL as a ``KeyError`` at import.

One settings object, validated at start-up, with production-grade defaults
refused where they would be unsafe.
"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

__all__ = ["Settings", "get_settings", "ConfigurationError"]

SERVICE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SERVICE_ROOT.parents[1]

#: The placeholder that shipped as the default signing key. Refused outright.
_INSECURE_KEYS = {
    "your-secret-key-change-this-in-production-use-openssl-rand-hex-32",
    "your-super-secret-key-change-in-production",
    "changeme",
    "secret",
}


class ConfigurationError(RuntimeError):
    """Raised when the service is configured in a way that cannot work."""


def _load_env() -> None:
    for candidate in (SERVICE_ROOT / ".env", REPO_ROOT / ".env"):
        if candidate.is_file():
            load_dotenv(dotenv_path=candidate, override=False)


def _env(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key, default)
    if value is None:
        return None
    value = value.strip().strip('"').strip("'")
    return value or None


def _env_bool(key: str, default: bool) -> bool:
    raw = _env(key)
    return default if raw is None else raw.lower() in {"1", "true", "yes", "y", "on"}


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{key} must be an integer, got {raw!r}") from exc


def _env_list(key: str, default: list[str]) -> list[str]:
    """Accept both a JSON array and a comma-separated list."""
    raw = _env(key)
    if not raw:
        return list(default)
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(f"{key} is not valid JSON: {raw!r}") from exc
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class DatabaseSettings:
    url: str
    pool_size: int
    max_overflow: int
    pool_timeout: int
    pool_recycle: int
    statement_timeout_ms: int
    echo: bool


@dataclass(frozen=True)
class SecuritySettings:
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    bcrypt_rounds: int
    generated_secret: bool


@dataclass(frozen=True)
class RedisSettings:
    enabled: bool
    host: str
    port: int
    db: int
    password: str | None

    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


@dataclass(frozen=True)
class S3Settings:
    bucket: str | None
    region: str
    access_key_id: str | None
    secret_access_key: str | None
    forms_prefix: str

    @property
    def configured(self) -> bool:
        return bool(self.bucket and self.access_key_id and self.secret_access_key)


@dataclass(frozen=True)
class Settings:
    env: str
    debug: bool
    log_level: str
    log_json: bool
    api_title: str
    api_version: str
    root_path: str
    cors_origins: list[str]
    cors_allow_credentials: bool
    rate_limit_per_minute: int
    max_page_size: int
    default_page_size: int
    database: DatabaseSettings
    security: SecuritySettings
    redis: RedisSettings
    s3: S3Settings
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"prod", "production"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env()

    env = _env("APP_ENV", "development") or "development"
    is_production = env.lower() in {"prod", "production"}
    warnings: list[str] = []

    # -- database ---------------------------------------------------------- #
    database_url = _env("DATABASE_URL")
    if not database_url:
        host = _env("POSTGRES_HOST", "localhost")
        port = _env("POSTGRES_PORT", "5432")
        name = _env("POSTGRES_DB") or _env("POSTGRES_DBNAME", "values_db")
        user = _env("POSTGRES_USER", "user")
        password = _env("POSTGRES_PASSWORD")
        if not password:
            raise ConfigurationError(
                "Set DATABASE_URL, or POSTGRES_PASSWORD together with the other POSTGRES_* variables."
            )
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        warnings.append("DATABASE_URL was assembled from the POSTGRES_* variables.")

    # -- security ---------------------------------------------------------- #
    secret_key = _env("SECRET_KEY")
    generated = False
    if not secret_key or secret_key in _INSECURE_KEYS:
        if is_production:
            raise ConfigurationError(
                "SECRET_KEY is missing or is a known placeholder. Generate one with "
                "`openssl rand -hex 32` before running in production."
            )
        secret_key = secrets.token_hex(32)
        generated = True
        warnings.append(
            "SECRET_KEY was not set; a random one was generated. Tokens will not "
            "survive a restart and will not be valid across workers."
        )

    # -- CORS -------------------------------------------------------------- #
    cors_origins = _env_list(
        "CORS_ORIGINS", ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    if "*" in cors_origins and is_production:
        raise ConfigurationError(
            "CORS_ORIGINS may not be '*' in production while credentials are allowed."
        )

    return Settings(
        env=env,
        debug=_env_bool("DEBUG", not is_production),
        log_level=(_env("LOG_LEVEL", "INFO") or "INFO").upper(),
        log_json=_env_bool("LOG_JSON", is_production),
        api_title=_env("API_TITLE", "FraudGuard Compliance API") or "FraudGuard Compliance API",
        api_version="2.0.0",
        root_path=_env("ROOT_PATH", "") or "",
        cors_origins=cors_origins,
        cors_allow_credentials=_env_bool("CORS_ALLOW_CREDENTIALS", True),
        rate_limit_per_minute=_env_int("RATE_LIMIT_PER_MINUTE", 300),
        max_page_size=_env_int("MAX_PAGE_SIZE", 500),
        default_page_size=_env_int("DEFAULT_PAGE_SIZE", 50),
        database=DatabaseSettings(
            url=database_url,
            pool_size=_env_int("DB_POOL_SIZE", 20),
            max_overflow=_env_int("DB_MAX_OVERFLOW", 40),
            pool_timeout=_env_int("DB_POOL_TIMEOUT", 30),
            pool_recycle=_env_int("DB_POOL_RECYCLE", 3600),
            statement_timeout_ms=_env_int("DB_STATEMENT_TIMEOUT_MS", 30000),
            echo=_env_bool("SQLALCHEMY_ECHO", False),
        ),
        security=SecuritySettings(
            secret_key=secret_key,
            algorithm=_env("JWT_ALGORITHM", "HS256") or "HS256",
            access_token_expire_minutes=_env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 480),
            refresh_token_expire_days=_env_int("REFRESH_TOKEN_EXPIRE_DAYS", 7),
            bcrypt_rounds=_env_int("BCRYPT_ROUNDS", 12),
            generated_secret=generated,
        ),
        redis=RedisSettings(
            enabled=_env_bool("REDIS_ENABLED", False),
            host=_env("REDIS_HOST", "localhost") or "localhost",
            port=_env_int("REDIS_PORT", 6379),
            db=_env_int("REDIS_DB", 0),
            password=_env("REDIS_PASSWORD"),
        ),
        s3=S3Settings(
            bucket=_env("AWS_S3_BUCKET") or _env("AWS_BUCKET_NAME"),
            region=_env("AWS_REGION", "eu-north-1") or "eu-north-1",
            access_key_id=_env("AWS_ACCESS_KEY_ID"),
            secret_access_key=_env("AWS_SECRET_ACCESS_KEY"),
            forms_prefix=_env("AWS_FORMS_PREFIX", "forms/pending/") or "forms/pending/",
        ),
        warnings=tuple(warnings),
    )
