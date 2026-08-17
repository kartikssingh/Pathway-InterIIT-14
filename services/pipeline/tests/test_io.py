from __future__ import annotations

import json
from datetime import datetime

import pytest

from fraudguard.io import jsonl
from fraudguard.io.state import StateStore


class TestJsonl:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "records.jsonl"
        jsonl.append_jsonl(path, {"a": 1})
        jsonl.append_jsonl(path, {"a": 2})
        assert jsonl.read_jsonl(path) == [{"a": 1}, {"a": 2}]

    def test_malformed_lines_are_skipped_not_fatal(self, tmp_path):
        path = tmp_path / "records.jsonl"
        path.write_text('{"a": 1}\nnot json at all\n\n{"a": 2}\n')
        assert jsonl.read_jsonl(path) == [{"a": 1}, {"a": 2}]

    def test_missing_file_returns_empty(self, tmp_path):
        assert jsonl.read_jsonl(tmp_path / "nope.jsonl") == []

    def test_datetimes_are_serialised(self, tmp_path):
        path = tmp_path / "records.jsonl"
        jsonl.append_jsonl(path, {"when": datetime(2025, 1, 2, 3, 4, 5)})
        assert jsonl.read_jsonl(path)[0]["when"] == "2025-01-02T03:04:05"

    def test_field_values_supports_dotted_paths(self, tmp_path):
        path = tmp_path / "reports.jsonl"
        jsonl.append_jsonl(path, {"risk_json": {"risk_score": 0.4}})
        jsonl.append_jsonl(path, {"risk_json": {"risk_score": 0.9}})
        assert jsonl.field_values(path, "risk_json.risk_score", default=0.0, coerce=float) == [
            0.4,
            0.9,
        ]

    def test_field_values_uses_the_default_when_absent(self, tmp_path):
        path = tmp_path / "reports.jsonl"
        jsonl.append_jsonl(path, {"other": 1})
        assert jsonl.field_values(path, "risk_json.risk_score", default=0.0, coerce=float) == [0.0]

    def test_write_jsonl_replaces_atomically(self, tmp_path):
        path = tmp_path / "records.jsonl"
        jsonl.append_jsonl(path, {"stale": True})
        jsonl.write_jsonl(path, [{"fresh": 1}, {"fresh": 2}])
        assert jsonl.read_jsonl(path) == [{"fresh": 1}, {"fresh": 2}]

    def test_one_record_is_one_line(self, tmp_path):
        path = tmp_path / "records.jsonl"
        jsonl.append_jsonl(path, {"text": "a\nb"})
        assert len(path.read_text().splitlines()) == 1
        assert json.loads(path.read_text())["text"] == "a\nb"


class TestStateStore:
    def test_save_and_load_latest(self, isolated_settings):
        store = StateStore("unit")
        store.save("entity-1", {"prompt": "first"})
        store.save("entity-1", {"prompt": "second"})
        assert store.load_latest("entity-1") == {"prompt": "second"}

    def test_load_previous_returns_the_prior_snapshot(self, isolated_settings):
        store = StateStore("unit")
        store.save("entity-1", {"prompt": "first"})
        store.save("entity-1", {"prompt": "second"})
        assert store.load_previous("entity-1") == {"prompt": "first"}

    def test_keys_do_not_leak_into_each_other(self, isolated_settings):
        """Regression: run-level directories mixed entities together."""
        store = StateStore("unit")
        store.save("entity-1", {"prompt": "one"})
        store.save("entity-2", {"prompt": "two"})
        assert store.load_latest("entity-1") == {"prompt": "one"}
        assert store.load_latest("entity-2") == {"prompt": "two"}

    def test_missing_key_returns_the_default(self, isolated_settings):
        assert StateStore("unit").load_latest("nobody", default={"x": 1}) == {"x": 1}

    def test_metadata_is_preserved(self, isolated_settings):
        store = StateStore("unit")
        store.save("entity-1", {"a": 1}, metadata={"similarity_vs_previous": 0.5})
        assert store.entries("entity-1")[0].metadata["similarity_vs_previous"] == 0.5

    def test_prune_keeps_the_most_recent(self, isolated_settings):
        store = StateStore("unit", retention_days=0)
        for index in range(8):
            store.save("entity-1", {"n": index})
        store.prune(keep_last=3)
        assert len(store.entries("entity-1")) == 3
        assert store.load_latest("entity-1") == {"n": 7}

    def test_uncompressed_mode(self, isolated_settings):
        store = StateStore("plain", compress=False)
        path = store.save("entity-1", {"a": 1})
        assert path.suffix == ".json"
        assert store.load_latest("entity-1") == {"a": 1}

    def test_backup_failure_does_not_break_the_save(self, isolated_settings):
        def exploding_uploader(_path, _key):
            raise RuntimeError("S3 is down")

        store = StateStore("unit", uploader=exploding_uploader)
        store.save("entity-1", {"a": 1})
        assert store.load_latest("entity-1") == {"a": 1}

    @pytest.mark.parametrize("key", ["a/b", "a b", "../escape"])
    def test_keys_are_slugified_into_safe_filenames(self, isolated_settings, key):
        store = StateStore("unit")
        path = store.save(key, {"a": 1})
        assert path.parent == store.root
        assert store.load_latest(key) == {"a": 1}
