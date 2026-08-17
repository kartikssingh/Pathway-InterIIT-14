"""Reusable Pathway UDFs and pure helpers.

Consolidates the two divergent copies of ``utils.py`` that used to live in the
repository.  Every UDF here is a thin wrapper around a plain Python function of
the same name prefixed with ``_``, so the logic is unit-testable without a
Pathway runtime.
"""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Sequence

import pandas as pd
import pathway as pw

from fraudguard import scoring
from fraudguard.logging import get_logger

__all__ = [
    "to_lower",
    "to_int_safe",
    "to_float_safe",
    "sha256_hex",
    "sha256_signature",
    "parse_date",
    "now_naive",
    "risk_from_score",
    "extract_json_and_summary",
    "parse_authenticity_score",
    "as_dict",
    "coalesce_float",
    "coalesce_int",
    "join_list",
]

log = get_logger("fraudguard.udfs")

_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d %B %Y", "%d %b %Y")

# ``<SUMMARY>`` is the tag the prompt asks for; bare ``SUMMARY`` is tolerated
# because older prompt revisions emitted it.
_SUMMARY_RE = re.compile(r"<SUMMARY>\s*(.*)|(?:^|\n)SUMMARY\s*\n(.*)", re.DOTALL)
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{.*?\}", re.DOTALL)


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #


def _to_lower(value: Any) -> str | None:
    return value.lower().strip() if isinstance(value, str) else None


def _to_int_safe(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float_safe(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        # Tolerate "₹12,00,000" / "12 lakh" style inputs from OCR.
        digits = re.sub(r"[^0-9.\-]", "", str(value))
        try:
            number = float(digits)
        except ValueError:
            return None
    return number


def _sha256_hex(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_signature(name: str | None, identifier: Any) -> str:
    return hashlib.sha256(f"{name or ''}{identifier}".encode("utf-8")).hexdigest()


def _parse_date(value: str | None) -> Any:
    """Parse a date string into a pandas Timestamp Pathway can serialise as DATE."""
    if not value:
        return None
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return pd.to_datetime(text, format=fmt, errors="raise")
        except (ValueError, TypeError):
            continue
    try:
        # Last resort: let pandas guess, but keep day-first (Indian KYC forms).
        return pd.to_datetime(text, dayfirst=True, errors="raise")
    except (ValueError, TypeError):
        log.warning("Unparseable date", extra={"value": text[:40]})
        return None


def _extract_json_and_summary(text: str) -> tuple[dict[str, Any], str | None]:
    """Split a compliance completion into its JSON verdict and prose summary.

    Returns ``({}, None)`` rather than raising, so a malformed completion
    degrades to the deterministic fallback instead of killing the flow.  The
    original version crashed with ``TypeError: 'NoneType' object does not
    support item assignment`` whenever the model omitted the fence.
    """
    import json

    payload: dict[str, Any] = {}
    fenced = _JSON_FENCE_RE.search(text or "")
    candidates = [fenced.group(1)] if fenced else []
    candidates.extend(match.group(0) for match in _JSON_OBJECT_RE.finditer(text or ""))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict) and "risk_score" in parsed:
            payload = parsed
            break
        if isinstance(parsed, dict) and not payload:
            payload = parsed

    summary: str | None = None
    match = _SUMMARY_RE.search(text or "")
    if match:
        summary = (match.group(1) or match.group(2) or "").strip() or None
    return payload, summary


def _parse_authenticity_score(text: str) -> float:
    """Pull ``authenticity_score`` out of a model response; -1.0 when absent."""
    import json

    if not text:
        return -1.0
    stripped = text.strip()
    start, end = stripped.find("{"), stripped.rfind("}") + 1
    if start == -1 or end <= start:
        return -1.0
    try:
        payload = json.loads(stripped[start:end])
    except json.JSONDecodeError:
        return -1.0
    raw = payload.get("authenticity_score") if isinstance(payload, dict) else None
    return -1.0 if raw is None else scoring.clamp01(raw)


# --------------------------------------------------------------------------- #
# Pathway UDFs
# --------------------------------------------------------------------------- #


@pw.udf
def to_lower(value: str | None) -> str | None:
    return _to_lower(value)


@pw.udf
def to_int_safe(value: str | None) -> int | None:
    return _to_int_safe(value)


@pw.udf
def to_float_safe(value: Any) -> float | None:
    return _to_float_safe(value)


@pw.udf
def coalesce_float(value: Any) -> float:
    result = _to_float_safe(value)
    return 0.0 if result is None else result


@pw.udf
def coalesce_int(value: Any) -> int:
    result = _to_int_safe(value)
    return 0 if result is None else result


@pw.udf
def sha256_hex(value: str | None) -> str | None:
    return _sha256_hex(value)


@pw.udf
def sha256_signature(name: str, identifier: int) -> str:
    return _sha256_signature(name, identifier)


@pw.udf
def parse_date(value: str | None) -> pw.DateTimeNaive | None:
    return _parse_date(value)


@pw.udf
def now_naive(_ignored: Any = None) -> pw.DateTimeNaive:
    """Current wall-clock time as a naive timestamp (Postgres ``TIMESTAMP``)."""
    return pd.to_datetime(time.time(), unit="s")


@pw.udf
def risk_from_score(score: float | None) -> dict:
    """Deterministic risk verdict from an OpenSanctions match score.

    Emits the same 0-1 ``risk_score`` scale as the LLM contract.  The previous
    implementation returned a 0-100 integer here while the LLM path returned
    0-1, so the two disagreed by a factor of 100 whenever the fallback fired.
    """
    return scoring.from_opensanctions_score(score).to_risk_json()


@pw.udf
def extract_json_and_summary(text: str) -> tuple[dict, str]:
    payload, summary = _extract_json_and_summary(text)
    return payload, summary or ""


@pw.udf
def parse_authenticity_score(text: str) -> float:
    return _parse_authenticity_score(text)


@pw.udf
def as_dict(**columns: Any) -> dict:
    """Bundle named columns into a single dict column (feature vectors)."""
    return dict(columns)


@pw.udf
def join_list(values: Sequence[str] | None, separator: str = ", ") -> str:
    if not values:
        return ""
    return separator.join(str(value) for value in values)
