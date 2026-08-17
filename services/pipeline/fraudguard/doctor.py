"""Pre-flight diagnostics: ``python -m fraudguard doctor``.

Answers "why won't this start?" in one command instead of by reading a
``KeyError`` traceback.  Every check is independent and non-destructive: it
reports what is configured, what is reachable and what is missing, and exits
non-zero only when something *required* is broken.

New in this refactor — the original had no way to validate an environment short
of starting all nine processes and watching which ones died.
"""

from __future__ import annotations

import argparse
import socket
import sys
from dataclasses import dataclass
from typing import Callable, Sequence
from urllib.parse import urlparse

from fraudguard.logging import configure

OK = "PASS"
WARN = "WARN"
FAIL = "FAIL"

_SYMBOL = {OK: "✓", WARN: "!", FAIL: "✗"}


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str = ""


Check = Callable[[], CheckResult]


# --------------------------------------------------------------------------- #
# Individual checks
# --------------------------------------------------------------------------- #


def check_config() -> CheckResult:
    try:
        from fraudguard.config import get_settings

        settings = get_settings()
    except Exception as exc:
        return CheckResult("configuration", FAIL, str(exc))
    return CheckResult(
        "configuration",
        OK,
        f"env={settings.env} log_level={settings.log_level} out={settings.paths.out}",
    )


def check_credentials() -> CheckResult:
    from fraudguard.config import get_settings

    settings = get_settings()
    present, absent = [], []
    for label, value in (
        ("OS_API_KEY", settings.enrichment.opensanctions_key),
        ("SANCTIONS_API_KEY", settings.enrichment.ofac_key),
        ("OTX_API_KEY", settings.enrichment.otx_key),
        ("MISTRAL_KEY", settings.llm.mistral_key),
        ("GEMINI_API_KEY", settings.llm.gemini_key),
        ("PW_LICENSE", settings.pathway_license),
        ("POSTGRES_PASSWORD", settings.postgres.password),
        ("AWS_ACCESS_KEY_ID", settings.aws.access_key_id),
        ("PROCESSOR_NAME", settings.gcp_processor_name),
    ):
        (present if value else absent).append(label)

    search_pairs = len(settings.enrichment.google_search_keys)
    detail = f"set: {', '.join(present) or 'none'}"
    if absent:
        detail += f" | missing: {', '.join(absent)}"
    detail += f" | search key pairs: {search_pairs}"
    status = OK if not absent else WARN
    return CheckResult("credentials", status, detail)


def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_kafka() -> CheckResult:
    from fraudguard.config import get_settings

    servers = get_settings().kafka.bootstrap_servers
    first = servers.split(",")[0].strip()
    host, _, port = first.partition(":")
    if not _port_open(host or "localhost", int(port or 9092)):
        return CheckResult("kafka", FAIL, f"cannot reach {first} — is the broker up?")
    return CheckResult("kafka", OK, f"reachable at {first}")


def check_postgres() -> CheckResult:
    from fraudguard.config import get_settings
    from fraudguard.io import postgres

    settings = get_settings().postgres
    if not settings.password:
        return CheckResult("postgres", WARN, "POSTGRES_PASSWORD not set; skipped")
    try:
        row = postgres.fetch_one("SELECT version()")
    except Exception as exc:
        return CheckResult("postgres", FAIL, f"{settings.host}:{settings.port} — {exc}")
    finally:
        postgres.close_pool()
    version = str(row[0]).split(",")[0] if row else "unknown"
    return CheckResult("postgres", OK, f"{settings.dbname} @ {settings.host} ({version})")


def check_tables() -> CheckResult:
    from fraudguard.config import get_settings
    from fraudguard.io import postgres

    if not get_settings().postgres.password:
        return CheckResult("schema", WARN, "skipped (no POSTGRES_PASSWORD)")
    expected = {
        "users",
        "transactions",
        "toxicityhistory",
        "usersanctionmatches",
        "staging_buffer",
        "compliance_alerts",
        "admins",
        "audit_logs",
        "system_metrics",
        "system_health",
        "system_alerts",
    }
    try:
        rows = postgres.fetch_all(
            "SELECT LOWER(table_name) FROM information_schema.tables WHERE table_schema = 'public'"
        )
    except Exception as exc:
        return CheckResult("schema", FAIL, str(exc))
    finally:
        postgres.close_pool()

    found = {row[0] for row in rows}
    missing = sorted(expected - found)
    if missing:
        return CheckResult(
            "schema", FAIL, f"missing tables: {', '.join(missing)} — run infra/bootstrap.sh"
        )
    return CheckResult("schema", OK, f"{len(expected)} expected tables present")


def check_models() -> CheckResult:
    from fraudguard.rps.registry import get_registry

    registry = get_registry()
    missing = registry.missing()
    if missing:
        return CheckResult("models", FAIL, f"missing artefacts: {', '.join(missing)}")
    return CheckResult(
        "models",
        OK,
        f"version {registry.version}, {len(registry.training_features())} features",
    )


def check_scorer() -> CheckResult:
    from fraudguard.config import get_settings

    url = get_settings().rps_score_url
    parsed = urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not _port_open(parsed.hostname or "127.0.0.1", port):
        return CheckResult("scorer", WARN, f"{url} not listening (rps-explain will score in-process)")
    return CheckResult("scorer", OK, f"listening at {url}")


def check_guardrails() -> CheckResult:
    from fraudguard.llm import guard

    if guard.is_active():
        return CheckResult("guardrails", OK, "toxicity and profanity validators loaded")
    return CheckResult(
        "guardrails",
        WARN,
        "not active — install guardrails-ai and its hub validators, or set GUARDRAILS_ENABLED=false",
    )


def check_optional_packages() -> CheckResult:
    import importlib.util

    optional = {
        "pathway": "the streaming engine (required for every flow)",
        "newsplease": "primary article extractor",
        "newspaper": "fallback article extractor",
        "sklearn": "TF-IDF similarity (a pure-Python fallback exists)",
        "OTXv2": "AlienVault threat intel",
        "crewai": "MCP agent",
        "deepface": "face matching",
        "faiss": "face index",
        "boto3": "S3 form intake",
    }
    missing = [
        f"{name} ({why})"
        for name, why in optional.items()
        if importlib.util.find_spec(name) is None
    ]
    if "pathway" in " ".join(missing):
        return CheckResult("packages", FAIL, "pathway is not installed")
    if missing:
        return CheckResult("packages", WARN, "not installed: " + "; ".join(missing))
    return CheckResult("packages", OK, "all optional integrations available")


CHECKS: tuple[tuple[str, Check], ...] = (
    ("config", check_config),
    ("packages", check_optional_packages),
    ("credentials", check_credentials),
    ("models", check_models),
    ("kafka", check_kafka),
    ("postgres", check_postgres),
    ("schema", check_tables),
    ("scorer", check_scorer),
    ("guardrails", check_guardrails),
)


def run_checks(only: Sequence[str] | None = None) -> list[CheckResult]:
    results: list[CheckResult] = []
    for name, check in CHECKS:
        if only and name not in only:
            continue
        try:
            results.append(check())
        except Exception as exc:  # a broken check must not hide the others
            results.append(CheckResult(name, FAIL, f"check itself failed: {exc}"))
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose the pipeline environment.")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        choices=[name for name, _ in CHECKS],
        help="Run only these checks (repeatable).",
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    args = parser.parse_args(argv)

    configure("doctor")
    results = run_checks(args.only or None)

    width = max(len(result.name) for result in results)
    print("\nFraudGuard environment check\n" + "=" * 60)
    for result in results:
        print(f" {_SYMBOL[result.status]} {result.name.ljust(width)}  {result.detail}")
    print("=" * 60)

    failures = sum(1 for result in results if result.status == FAIL)
    warnings = sum(1 for result in results if result.status == WARN)
    print(f" {len(results) - failures - warnings} passed, {warnings} warnings, {failures} failures\n")

    if failures:
        return 1
    return 1 if (args.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
