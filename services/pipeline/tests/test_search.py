"""Search key rotation.

The original loop retried forever on a 5xx and permanently disqualified a key
after one quota error; these pin down the replacement behaviour.
"""

from __future__ import annotations

import pytest

from fraudguard.enrichment import search
from fraudguard.errors import RateLimitedError, UpstreamError


@pytest.fixture
def pool():
    return search.SearchKeyPool(
        keys=[search._Key("key-1", "cx-1"), search._Key("key-2", "cx-2")]
    )


class TestKeyPool:
    def test_rotates_round_robin(self, pool):
        first = pool.next_key()
        second = pool.next_key()
        assert first is not second
        assert pool.next_key() is first

    def test_cooling_keys_are_skipped(self, pool):
        first = pool.next_key()
        pool.cool_off(first)
        for _ in range(4):
            assert pool.next_key() is not first

    def test_returns_none_when_everything_is_cooling(self, pool):
        for key in list(pool.keys):
            pool.cool_off(key)
        assert pool.next_key() is None

    def test_empty_pool_is_falsy(self):
        assert not search.SearchKeyPool()


class TestSearch:
    def test_quota_error_rotates_to_the_next_key(self, pool, monkeypatch):
        seen: list[str] = []

        def fake_query(key, _query, _num):
            seen.append(key.api_key)
            if key.api_key == "key-1":
                raise RateLimitedError("google-cse", "quota", status_code=429)
            return ["https://example.com/a"]

        monkeypatch.setattr(search, "_query_once", fake_query)
        assert search.search("q", pool) == ["https://example.com/a"]
        assert seen == ["key-1", "key-2"]

    def test_gives_up_instead_of_looping_forever(self, pool, monkeypatch):
        """Regression: a persistent 5xx spun at 5-second intervals indefinitely."""
        calls = {"n": 0}

        def always_fails(_key, _query, _num):
            calls["n"] += 1
            raise UpstreamError("google-cse", "boom", status_code=503)

        monkeypatch.setattr(search, "_query_once", always_fails)
        monkeypatch.setattr(search.time, "sleep", lambda _s: None)
        assert search.search("q", pool) == []
        assert calls["n"] <= search._MAX_ATTEMPTS_PER_QUERY

    def test_bad_credentials_retire_the_key_for_the_run(self, pool, monkeypatch):
        def unauthorised(_key, _query, _num):
            raise UpstreamError("google-cse", "bad key", status_code=403)

        monkeypatch.setattr(search, "_query_once", unauthorised)
        monkeypatch.setattr(search.time, "sleep", lambda _s: None)
        assert search.search("q", pool) == []
        assert all(not key.available for key in pool.keys)


class TestFindAdverseLinks:
    def test_deduplicates_across_keywords(self, isolated_settings, monkeypatch, pool):
        monkeypatch.setattr(search, "search", lambda *_a, **_k: ["https://example.com/a"])
        monkeypatch.setattr(search.time, "sleep", lambda _s: None)
        links = find = search.find_adverse_links(
            "Jane Doe", keywords=("fraud", "scam"), pool=pool, num_results=2
        )
        assert links == ["https://example.com/a"]
        assert find is links

    def test_no_keys_returns_empty_rather_than_raising(self, isolated_settings, monkeypatch):
        monkeypatch.setattr(search.SearchKeyPool, "from_settings", classmethod(lambda cls: cls()))
        assert search.find_adverse_links("Jane Doe") == []

    def test_blank_subject_short_circuits(self, isolated_settings, pool):
        assert search.find_adverse_links("   ", pool=pool) == []
