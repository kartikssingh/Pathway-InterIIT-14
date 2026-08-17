"""Centralised, validated configuration for every pipeline flow.

The original code read ``os.environ[...]`` at import time in a dozen modules, so a
single missing key crashed an unrelated flow with a bare ``KeyError``.  Everything
now goes through :func:`get_settings`, which

* reads ``.env`` once (searching upward from this file so any working directory works),
* coerces and validates values,
* reports *all* missing required keys for the flow you are actually running,
* exposes typed, immutable settings objects.

Nothing here performs I/O beyond reading the ``.env`` file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Mapping

from dotenv import load_dotenv

__all__ = [
    "ConfigError",
    "Settings",
    "KafkaSettings",
    "PostgresSettings",
    "LLMSettings",
    "EnrichmentSettings",
    "AWSSettings",
    "PathSettings",
    "get_settings",
    "require",
]


class ConfigError(RuntimeError):
    """Raised when configuration is missing or malformed."""


# --------------------------------------------------------------------------- #
# Environment loading
# --------------------------------------------------------------------------- #

#: Repository-relative root of the pipeline service (``services/pipeline``).
SERVICE_ROOT = Path(__file__).resolve().parents[1]

#: Monorepo root (``Pathway-InterIIT-14``).
REPO_ROOT = SERVICE_ROOT.parents[1]


def _load_dotenv_once() -> None:
    """Load the first ``.env`` found in the service dir, then the repo root."""
    for candidate in (SERVICE_ROOT / ".env", REPO_ROOT / ".env"):
        if candidate.is_file():
            load_dotenv(dotenv_path=candidate, override=False)


def _env(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key, default)
    if value is None:
        return None
    value = value.strip().strip('"').strip("'")
    return value or None


def _env_bool(key: str, default: bool = False) -> bool:
    raw = _env(key)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "y", "on"}


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:  # pragma: no cover - configuration error path
        raise ConfigError(f"{key} must be an integer, got {raw!r}") from exc


def _env_float(key: str, default: float) -> float:
    raw = _env(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:  # pragma: no cover - configuration error path
        raise ConfigError(f"{key} must be a number, got {raw!r}") from exc


def require(settings: "Settings", keys: Iterable[str]) -> None:
    """Fail fast when a flow needs credentials that were not supplied.

    Reports every missing key at once instead of dying on the first one.
    """
    missing = [key for key in keys if not _env(key)]
    if missing:
        raise ConfigError(
            "Missing required environment variables: "
            + ", ".join(sorted(missing))
            + f"\nCopy {REPO_ROOT / '.env.example'} to "
            + f"{SERVICE_ROOT / '.env'} and fill them in."
        )


# --------------------------------------------------------------------------- #
# Setting groups
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class KafkaSettings:
    bootstrap_servers: str
    group_id: str
    session_timeout_ms: str
    auto_offset_reset: str

    # Topics
    entities_topic: str
    db_updates_topic: str
    fraud_topic: str
    rps_features_topic: str
    transactions_cdc_topic: str

    autocommit_duration_ms: int

    def rdkafka(self, *, group_suffix: str | None = None) -> dict[str, str]:
        """librdkafka settings dict consumed by ``pw.io.kafka``.

        ``group_suffix`` gives each flow its own consumer group so two flows
        reading the same topic do not steal each other's partitions — the
        original code hard-coded ``group.id=0`` everywhere, which silently
        load-balanced unrelated consumers against one another.
        """
        group = self.group_id if group_suffix is None else f"{self.group_id}-{group_suffix}"
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": group,
            "session.timeout.ms": self.session_timeout_ms,
            "auto.offset.reset": self.auto_offset_reset,
        }


@dataclass(frozen=True)
class PostgresSettings:
    host: str
    port: str
    dbname: str
    user: str
    password: str | None

    @property
    def connection_parts(self) -> dict[str, str]:
        """Mapping accepted by ``pw.io.postgres.write``."""
        if not self.password:
            raise ConfigError("POSTGRES_PASSWORD is required to write to Postgres.")
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
        }

    @property
    def dsn(self) -> str:
        password = self.password or ""
        return f"postgresql://{self.user}:{password}@{self.host}:{self.port}/{self.dbname}"


@dataclass(frozen=True)
class LLMSettings:
    chat_model: str
    embedding_model: str
    cross_encoder_model: str | None
    mistral_key: str | None
    embedding_api_key: str | None
    gemini_key: str | None
    agent_model: str
    max_retries: int
    request_timeout_s: int
    guardrails_enabled: bool
    toxicity_threshold: float


@dataclass(frozen=True)
class EnrichmentSettings:
    opensanctions_key: str | None
    opensanctions_url: str
    ofac_key: str | None
    ofac_url: str
    otx_key: str | None
    google_search_keys: tuple[tuple[str, str], ...]
    adverse_keywords: tuple[str, ...]
    results_per_query: int
    http_timeout_s: int
    http_retries: int
    cache_size: int


@dataclass(frozen=True)
class AWSSettings:
    region: str
    access_key_id: str | None
    secret_access_key: str | None
    forms_bucket: str
    forms_prefix: str
    profile_pic_bucket: str

    @property
    def forms_uri(self) -> str:
        return f"s3://{self.forms_bucket}/{self.forms_prefix}"


@dataclass(frozen=True)
class PathSettings:
    service_root: Path
    inbox: Path
    out: Path
    state: Path
    logs: Path
    ml_root: Path

    def ensure(self) -> "PathSettings":
        for directory in (self.inbox, self.out, self.state, self.logs):
            directory.mkdir(parents=True, exist_ok=True)
        return self


@dataclass(frozen=True)
class Settings:
    env: str
    log_level: str
    log_json: bool
    pathway_license: str | None
    mcp_url: str
    rps_score_url: str
    rag_url: str
    rps_api_host: str
    rps_api_port: int
    kafka: KafkaSettings
    postgres: PostgresSettings
    llm: LLMSettings
    enrichment: EnrichmentSettings
    aws: AWSSettings
    paths: PathSettings
    gcp_processor_name: str | None
    gcp_credentials_path: str | None
    metadata: Mapping[str, str] = field(default_factory=dict)

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"prod", "production"}


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _collect_search_keys() -> tuple[tuple[str, str], ...]:
    """Collect the numbered ``GOOGLE_CLOUD_API_KEY_n``/``PROGRAMMABLE_SEARCH_ENGINE_ID_n`` pairs.

    The original loop stopped at the first gap; this one scans a fixed window so
    a hole in the numbering does not silently drop the remaining keys.
    """
    pairs: list[tuple[str, str]] = []
    for index in range(1, 21):
        key = _env(f"GOOGLE_CLOUD_API_KEY_{index}")
        engine = _env(f"PROGRAMMABLE_SEARCH_ENGINE_ID_{index}")
        if key and engine:
            pairs.append((key, engine))
    return tuple(pairs)


def _build_paths() -> PathSettings:
    root = Path(_env("PIPELINE_ROOT") or SERVICE_ROOT).resolve()
    return PathSettings(
        service_root=root,
        inbox=Path(_env("INBOX_DIR") or root / "inbox").resolve(),
        out=Path(_env("OUT_DIR") or root / "out").resolve(),
        state=Path(_env("STATE_DIR") or root / "state").resolve(),
        logs=Path(_env("LOG_DIR") or root / "logs").resolve(),
        ml_root=Path(_env("ML_ROOT") or root / "ml").resolve(),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    _load_dotenv_once()

    kafka = KafkaSettings(
        bootstrap_servers=_env("BOOTSTRAP_SERVERS", "localhost:9092") or "localhost:9092",
        group_id=_env("GROUP_ID", "fraudguard") or "fraudguard",
        session_timeout_ms=_env("SESSION_TIMEOUT_MS", "6000") or "6000",
        auto_offset_reset=_env("AUTO_OFFSET_RESET", "earliest") or "earliest",
        entities_topic=_env("MAIN_BACKEND_TOPIC", "entities") or "entities",
        db_updates_topic=_env("DB_TOPIC", "db_updates") or "db_updates",
        fraud_topic=_env("FRAUD_TOPIC", "possible_fraud") or "possible_fraud",
        rps_features_topic=_env("RPS_FEATURES_TOPIC", "rps_processed_features")
        or "rps_processed_features",
        transactions_cdc_topic=_env("TRANSACTIONS_CDC_TOPIC", "postgres.public.transactions")
        or "postgres.public.transactions",
        autocommit_duration_ms=_env_int("KAFKA_AUTOCOMMIT_MS", 100),
    )

    postgres = PostgresSettings(
        host=_env("POSTGRES_HOST", "localhost") or "localhost",
        port=_env("POSTGRES_PORT", "5432") or "5432",
        # Historically two different names were used for the same variable.
        dbname=_env("POSTGRES_DBNAME") or _env("POSTGRES_DB", "values_db") or "values_db",
        user=_env("POSTGRES_USER", "user") or "user",
        password=_env("POSTGRES_PASSWORD"),
    )

    llm = LLMSettings(
        chat_model=_env("LLM_MODEL", "mistral/mistral-small-latest")
        or "mistral/mistral-small-latest",
        embedding_model=_env("EMBEDDING_MODEL", "mistral/mistral-embed") or "mistral/mistral-embed",
        cross_encoder_model=_env("CROSS_ENCODER_MODEL"),
        mistral_key=_env("MISTRAL_KEY"),
        embedding_api_key=_env("EMBEDDING_API_KEY") or _env("MISTRAL_KEY"),
        gemini_key=_env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY"),
        agent_model=_env("AGENT_MODEL", "gemini-2.5-flash") or "gemini-2.5-flash",
        max_retries=_env_int("LLM_MAX_RETRIES", 4),
        request_timeout_s=_env_int("LLM_TIMEOUT_S", 60),
        guardrails_enabled=_env_bool("GUARDRAILS_ENABLED", True),
        toxicity_threshold=_env_float("GUARDRAILS_TOXICITY_THRESHOLD", 0.5),
    )

    enrichment = EnrichmentSettings(
        opensanctions_key=_env("OS_API_KEY"),
        opensanctions_url=_env("OS_API_URL", "https://api.opensanctions.org/match/default")
        or "https://api.opensanctions.org/match/default",
        ofac_key=_env("SANCTIONS_API_KEY"),
        ofac_url=_env("OFAC_API_URL", "https://api.ofac-api.com/v4") or "https://api.ofac-api.com/v4",
        otx_key=_env("OTX_API_KEY"),
        google_search_keys=_collect_search_keys(),
        adverse_keywords=tuple(
            keyword.strip()
            for keyword in (_env("ADVERSE_KEYWORDS", "fraud,scam") or "fraud,scam").split(",")
            if keyword.strip()
        ),
        results_per_query=_env_int("SEARCH_RESULTS_PER_QUERY", 2),
        http_timeout_s=_env_int("HTTP_TIMEOUT_S", 30),
        http_retries=_env_int("HTTP_RETRIES", 3),
        cache_size=_env_int("LOOKUP_CACHE_SIZE", 5000),
    )

    aws = AWSSettings(
        region=_env("AWS_REGION", "eu-north-1") or "eu-north-1",
        access_key_id=_env("AWS_ACCESS_KEY_ID"),
        secret_access_key=_env("AWS_SECRET_ACCESS_KEY"),
        forms_bucket=_env("AWS_BUCKET_NAME", "amzn-s3-pathway-bucket") or "amzn-s3-pathway-bucket",
        forms_prefix=_env("AWS_FORMS_PREFIX", "forms/pending/") or "forms/pending/",
        profile_pic_bucket=_env("AWS_PROFILEPIC_BUCKET", "amzn-s3-pathway-profilepic")
        or "amzn-s3-pathway-profilepic",
    )

    rps_host = _env("RPS_API_HOST", "127.0.0.1") or "127.0.0.1"
    rps_port = _env_int("RPS_API_PORT", 9000)

    return Settings(
        env=_env("APP_ENV", "development") or "development",
        log_level=(_env("LOG_LEVEL", "INFO") or "INFO").upper(),
        log_json=_env_bool("LOG_JSON", False),
        pathway_license=_env("PW_LICENSE"),
        mcp_url=_env("PATHWAY_MCP_URL", "http://localhost:8123/mcp/")
        or "http://localhost:8123/mcp/",
        rps_score_url=_env("SCORE_URL") or f"http://{rps_host}:{rps_port}/score",
        rag_url=_env("RAG_URL", "http://127.0.0.1:8000/v2/answer") or "http://127.0.0.1:8000/v2/answer",
        rps_api_host=rps_host,
        rps_api_port=rps_port,
        kafka=kafka,
        postgres=postgres,
        llm=llm,
        enrichment=enrichment,
        aws=aws,
        paths=_build_paths().ensure(),
        gcp_processor_name=_env("PROCESSOR_NAME"),
        gcp_credentials_path=_env("GOOGLE_APPLICATION_CREDENTIALS"),
    )
