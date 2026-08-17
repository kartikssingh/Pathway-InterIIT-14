"""OpenSanctions screening.

Improvements over the original ``open_sanctions.py``:

* one pooled, retrying HTTP session instead of a new ``requests.Session`` per call;
* the cache key is normalised across *all* query properties (previously only the
  name was lower-cased, so ``("Ravi", "1980-01-01")`` and ``("ravi", "1980-01-01")``
  were separate cache entries while ``alias`` differences were ignored);
* the full match list is retained (with the top hit surfaced) so downstream code
  can count matches instead of assuming exactly one;
* failures are reported through the error field rather than silently becoming
  ``score=None``, which used to be indistinguishable from "clean".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import pathway as pw

from fraudguard.errors import UpstreamError
from fraudguard.io.http import request_json
from fraudguard.logging import get_logger

__all__ = ["ScreeningResult", "screen", "os_lookup", "EMPTY_RESULT"]

log = get_logger("fraudguard.opensanctions")


@dataclass(frozen=True)
class ScreeningResult:
    entity_id: str | None = None
    entity_name: str | None = None
    score: float | None = None
    match_count: int = 0
    datasets: tuple[str, ...] = field(default_factory=tuple)
    data: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "score": self.score,
            "match_count": self.match_count,
            "datasets": list(self.datasets),
            "data": self.data,
            "error": self.error,
        }


EMPTY_RESULT = ScreeningResult()


def _normalise(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = " ".join(str(value).split()).strip().lower()
    return cleaned or None


def _query(
    name: str,
    birth_date: str | None,
    nationality: str | None,
    alias: str | None,
) -> ScreeningResult:
    from fraudguard.config import get_settings

    settings = get_settings().enrichment
    if not settings.opensanctions_key:
        return ScreeningResult(error="OS_API_KEY not configured")

    properties: dict[str, list[str]] = {"name": [name]}
    if birth_date:
        properties["birthDate"] = [birth_date]
    if nationality:
        properties["nationality"] = [nationality]
    if alias and alias != name:
        properties["alias"] = [alias]

    payload = {"queries": {"q": {"schema": "Person", "properties": properties}}}

    body = request_json(
        "POST",
        settings.opensanctions_url,
        service="opensanctions",
        headers={"Authorization": settings.opensanctions_key},
        json_body=payload,
    )

    results = (body.get("responses") or {}).get("q", {}).get("results") or []
    if not results:
        return ScreeningResult(match_count=0)

    # Results are returned score-descending; everything after the first is
    # usually ~0 because the per-query scores sum to 1.
    top = results[0]
    entity = top.get("entity") or {}
    names = (entity.get("properties") or {}).get("name") or []
    datasets = tuple(str(item) for item in (entity.get("datasets") or []))

    return ScreeningResult(
        entity_id=entity.get("id"),
        entity_name=names[0] if names else None,
        score=top.get("score"),
        match_count=sum(1 for item in results if (item.get("score") or 0) > 0),
        datasets=datasets,
        data=top,
    )


@lru_cache(maxsize=4096)
def _cached_screen(
    name: str,
    birth_date: str | None,
    nationality: str | None,
    alias: str | None,
) -> ScreeningResult:
    if not name:
        return EMPTY_RESULT
    try:
        return _query(name, birth_date, nationality, alias)
    except UpstreamError as exc:
        log.warning("OpenSanctions lookup failed", extra={"name": name, "error": str(exc)})
        return ScreeningResult(error=str(exc))


def screen(
    name: str | None,
    birth_date: str | None = None,
    nationality: str | None = None,
    alias: str | None = None,
) -> ScreeningResult:
    """Screen a person against OpenSanctions (memoised on the normalised query)."""
    return _cached_screen(
        _normalise(name) or "",
        _normalise(birth_date),
        _normalise(nationality),
        _normalise(alias),
    )


def clear_cache() -> None:
    _cached_screen.cache_clear()


@pw.udf(return_type=dict, deterministic=False)
def os_lookup(
    name: str | None,
    birth_date: str | None = None,
    nationality: str | None = None,
    alias: str | None = None,
) -> dict:
    """Pathway UDF returning the screening result as a plain dict."""
    return screen(name, birth_date, nationality, alias).to_dict()
