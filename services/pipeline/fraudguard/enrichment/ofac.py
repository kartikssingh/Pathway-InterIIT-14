"""OFAC sanctions screening (ofac-api.com).

Split out of ``mcp_server.py`` so the same screening logic can be used from the
MCP tool, a batch job or a test without starting a Pathway server.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import pathway as pw

from fraudguard.errors import UpstreamError
from fraudguard.io.http import request_json
from fraudguard.logging import get_logger

__all__ = ["OfacMatch", "screen", "ofac_screen"]

log = get_logger("fraudguard.ofac")


@dataclass(frozen=True)
class OfacMatch:
    query_name: str
    entity_id: str | None
    entity_name: str | None
    score: float | None
    programs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_name": self.query_name,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "score": self.score,
            "programs": list(self.programs),
        }


@lru_cache(maxsize=2048)
def _cached_screen(name: str) -> tuple[OfacMatch, ...]:
    from fraudguard.config import get_settings

    settings = get_settings().enrichment
    if not settings.ofac_key:
        log.debug("SANCTIONS_API_KEY not configured; OFAC screening skipped")
        return ()

    body = request_json(
        "POST",
        f"{settings.ofac_url}/screen",
        service="ofac",
        json_body={"apiKey": settings.ofac_key, "cases": [{"name": name}]},
    )

    matches: list[OfacMatch] = []
    for record in body.get("results", []) or []:
        for match in record.get("matches", []) or []:
            sanction = match.get("sanction") or {}
            matches.append(
                OfacMatch(
                    query_name=record.get("name", name),
                    entity_id=sanction.get("id"),
                    entity_name=sanction.get("name"),
                    score=match.get("score"),
                    programs=tuple(str(p) for p in (sanction.get("programs") or [])),
                )
            )
    return tuple(matches)


def screen(name: str | None) -> list[OfacMatch]:
    """Screen a name against the OFAC lists; never raises."""
    cleaned = " ".join((name or "").split()).strip().lower()
    if not cleaned:
        return []
    try:
        return list(_cached_screen(cleaned))
    except UpstreamError as exc:
        log.warning("OFAC lookup failed", extra={"name": cleaned, "error": str(exc)})
        return []


@pw.udf(return_type=dict, deterministic=False)
def ofac_screen(name: str) -> dict:
    """Pathway UDF: ``{"matches": [...], "match_count": n}``."""
    matches = screen(name)
    return {
        "query_name": name,
        "match_count": len(matches),
        "matches": [match.to_dict() for match in matches],
    }
