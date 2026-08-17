"""Source-reputation signals for a scraped article URL.

Formerly ``sus.py``.  Each check is optional, cached and non-fatal — a missing
OTX key or a slow Wayback response now degrades one signal instead of dropping
the whole article from the evidence set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from fraudguard.errors import UpstreamError
from fraudguard.io.http import get_session, request_json
from fraudguard.logging import get_logger

__all__ = [
    "ReputationSignals",
    "content_signals",
    "domain_history",
    "threat_intel",
    "assess_source",
]

log = get_logger("fraudguard.reputation")

_WAYBACK_URL = "http://archive.org/wayback/available"


@dataclass(frozen=True)
class ReputationSignals:
    url: str
    content_score: float = 0.0
    content_detail: dict[str, bool] = field(default_factory=dict)
    has_history: bool = False
    first_archived: str | None = None
    alexa_rank: str = "unknown"
    akamai_rank: str = "unknown"
    threat_pulses: int = 0
    threat_tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "domain": self.domain,
            "content_score": self.content_score,
            "content_detail": self.content_detail,
            "has_history": self.has_history,
            "first_archived": self.first_archived,
            "alexa_rank": self.alexa_rank,
            "akamai_rank": self.akamai_rank,
            "threat_pulses": self.threat_pulses,
            "threat_tags": list(self.threat_tags),
        }


def content_signals(url: str) -> tuple[float, dict[str, bool]]:
    """Score journalistic hygiene from the page's own markup (0-1)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover - optional dependency
        log.debug("beautifulsoup4 not installed; content signals skipped")
        return 0.0, {}

    try:
        response = get_session().get(url, timeout=20)
        response.raise_for_status()
    except Exception as exc:
        log.debug("Could not fetch page for content signals", extra={"url": url, "error": str(exc)})
        return 0.0, {}

    soup = BeautifulSoup(response.content, "html.parser")
    signals = {
        "has_author": bool(
            soup.find("meta", property="article:author") or soup.find("meta", attrs={"name": "author"})
        ),
        "has_date": bool(
            soup.find("meta", property="article:published_time")
            or soup.find("time", attrs={"datetime": True})
        ),
        "has_links": len(soup.find_all("a", href=True)) > 5,
        "has_schema": bool(soup.find("script", type="application/ld+json")),
        "uses_https": url.startswith("https://"),
    }
    score = sum(1 for value in signals.values() if value) / max(1, len(signals))
    return score, signals


@lru_cache(maxsize=2048)
def domain_history(url: str) -> tuple[bool, str | None]:
    """Ask the Wayback Machine whether the domain has any archived history."""
    try:
        body = request_json("GET", _WAYBACK_URL, service="wayback", params={"url": url}, timeout=15)
    except UpstreamError as exc:
        log.debug("Wayback lookup failed", extra={"url": url, "error": str(exc)})
        return False, None
    closest = (body.get("archived_snapshots") or {}).get("closest") or {}
    if closest:
        return True, closest.get("timestamp")
    return False, None


@lru_cache(maxsize=1024)
def threat_intel(url: str) -> tuple[str, str, int, tuple[str, ...]]:
    """AlienVault OTX reputation: (alexa_rank, akamai_rank, pulse_count, tags)."""
    from fraudguard.config import get_settings

    api_key = get_settings().enrichment.otx_key
    if not api_key:
        return "unknown", "unknown", 0, ()

    try:
        from OTXv2 import IndicatorTypes, OTXv2
    except ImportError:  # pragma: no cover - optional dependency
        log.debug("OTXv2 not installed; threat intel skipped")
        return "unknown", "unknown", 0, ()

    try:
        details = OTXv2(api_key).get_indicator_details_full(IndicatorTypes.URL, url)
    except Exception as exc:
        log.debug("OTX lookup failed", extra={"url": url, "error": str(exc)})
        return "unknown", "unknown", 0, ()

    validation = ((details.get("general") or {}).get("validation") or [])
    alexa = str(validation[0].get("message")) if len(validation) > 0 else "unknown"
    akamai = str(validation[1].get("message")) if len(validation) > 1 else "unknown"

    pulses = ((details.get("pulse_info") or {}).get("pulses") or [])
    tags = sorted({str(tag) for pulse in pulses for tag in (pulse.get("tags") or [])})
    return alexa, akamai, len(pulses), tuple(tags)


def assess_source(url: str) -> ReputationSignals:
    """Run every reputation check for a URL and bundle the results."""
    if not url:
        return ReputationSignals(url="")
    score, detail = content_signals(url)
    has_history, first_archived = domain_history(url)
    alexa, akamai, pulses, tags = threat_intel(url)
    return ReputationSignals(
        url=url,
        content_score=score,
        content_detail=detail,
        has_history=has_history,
        first_archived=first_archived,
        alexa_rank=alexa,
        akamai_rank=akamai,
        threat_pulses=pulses,
        threat_tags=tags,
    )
