"""Adverse-media discovery via the Google Programmable Search API.

Rewritten from ``adverse_media_finder.py``, which had two structural problems:

* an unbounded ``while not success`` loop — a persistent 5xx from Google spun
  forever at 5-second intervals with no ceiling;
* key rotation advanced a shared index permanently, so one exhausted key
  disqualified every *subsequent* keyword even after the quota window reset.

This version bounds the retries per keyword, rotates keys round-robin, marks a
key as cooling-off rather than dead, and returns whatever it managed to find.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable

from fraudguard.errors import RateLimitedError, UpstreamError
from fraudguard.io.http import request_json
from fraudguard.logging import get_logger

__all__ = ["SearchKeyPool", "find_adverse_links", "search"]

log = get_logger("fraudguard.search")

_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
_MAX_ATTEMPTS_PER_QUERY = 6
_COOLDOWN_SECONDS = 15 * 60


@dataclass
class _Key:
    api_key: str
    engine_id: str
    cooling_until: float = 0.0
    failures: int = 0

    @property
    def available(self) -> bool:
        return time.time() >= self.cooling_until


@dataclass
class SearchKeyPool:
    """Round-robin pool of Google API key / search-engine pairs."""

    keys: list[_Key] = field(default_factory=list)
    _cursor: int = 0

    @classmethod
    def from_settings(cls) -> "SearchKeyPool":
        from fraudguard.config import get_settings

        pairs = get_settings().enrichment.google_search_keys
        return cls(keys=[_Key(api_key=key, engine_id=engine) for key, engine in pairs])

    def __bool__(self) -> bool:
        return bool(self.keys)

    def next_key(self) -> _Key | None:
        """Next available key, or ``None`` if every key is cooling off."""
        for _ in range(len(self.keys)):
            key = self.keys[self._cursor % len(self.keys)]
            self._cursor += 1
            if key.available:
                return key
        return None

    def cool_off(self, key: _Key, seconds: float = _COOLDOWN_SECONDS) -> None:
        key.cooling_until = time.time() + seconds
        key.failures += 1
        log.warning(
            "Search key cooling off",
            extra={"seconds": int(seconds), "failures": key.failures},
        )


def _query_once(key: _Key, query: str, num_results: int) -> list[str]:
    body = request_json(
        "GET",
        _ENDPOINT,
        service="google-cse",
        params={"key": key.api_key, "cx": key.engine_id, "q": query, "num": num_results},
    )
    return [item["link"] for item in body.get("items", []) if item.get("link")]


def search(query: str, pool: SearchKeyPool, num_results: int = 2) -> list[str]:
    """Run one query, rotating keys on quota errors. Returns [] if it cannot."""
    for attempt in range(1, _MAX_ATTEMPTS_PER_QUERY + 1):
        key = pool.next_key()
        if key is None:
            log.error("All search keys are cooling off", extra={"query": query})
            return []
        try:
            return _query_once(key, query, num_results)
        except RateLimitedError:
            pool.cool_off(key)
        except UpstreamError as exc:
            if exc.status_code and 400 <= exc.status_code < 500:
                # Bad key or malformed engine id — retire it for this run.
                pool.cool_off(key, seconds=24 * 3600)
            else:
                backoff = min(2**attempt, 20)
                log.warning(
                    "Search transient failure",
                    extra={"query": query, "attempt": attempt, "backoff_s": backoff},
                )
                time.sleep(backoff)
    log.error("Search exhausted retries", extra={"query": query})
    return []


def find_adverse_links(
    subject: str,
    *,
    keywords: Iterable[str] | None = None,
    pool: SearchKeyPool | None = None,
    num_results: int | None = None,
) -> list[str]:
    """Search ``"<subject>" "<keyword>"`` for each adverse keyword.

    Returns a de-duplicated, order-stable list of URLs.
    """
    from fraudguard.config import get_settings

    settings = get_settings().enrichment
    subject = (subject or "").strip()
    if not subject:
        return []

    pool = pool or SearchKeyPool.from_settings()
    if not pool:
        log.warning(
            "No GOOGLE_CLOUD_API_KEY_n / PROGRAMMABLE_SEARCH_ENGINE_ID_n pairs configured; "
            "adverse-media search disabled"
        )
        return []

    keywords = tuple(keywords or settings.adverse_keywords)
    num_results = num_results or settings.results_per_query

    seen: dict[str, None] = {}
    for keyword in keywords:
        for link in search(f'"{subject}" "{keyword}"', pool, num_results):
            seen.setdefault(link, None)
        time.sleep(0.5)  # be polite to the API

    log.info(
        "Adverse-media search complete",
        extra={"subject": subject, "keywords": len(keywords), "links": len(seen)},
    )
    return list(seen)
