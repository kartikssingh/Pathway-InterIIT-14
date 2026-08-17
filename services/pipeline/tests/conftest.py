"""Test fixtures.

The settings singleton is cached, so every test that touches configuration must
clear it; ``isolated_settings`` does that and points every path at a tmpdir so a
test run never writes into the working tree.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Tests run against the checked-out tree, not an installed package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_BASE_ENV = {
    "APP_ENV": "test",
    "LOG_LEVEL": "WARNING",
    "BOOTSTRAP_SERVERS": "localhost:9092",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_DBNAME": "values_db_test",
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "OS_API_KEY": "test-os-key",
    "MISTRAL_KEY": "test-mistral-key",
    "GUARDRAILS_ENABLED": "false",
}


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    """A fresh Settings object rooted at a temporary directory."""
    from fraudguard import config

    for key, value in _BASE_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("PIPELINE_ROOT", str(tmp_path))
    monkeypatch.setenv("INBOX_DIR", str(tmp_path / "inbox"))
    monkeypatch.setenv("OUT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("ML_ROOT", str(tmp_path / "ml"))

    config.get_settings.cache_clear()
    settings = config.get_settings()
    yield settings
    config.get_settings.cache_clear()


@pytest.fixture
def clean_env(monkeypatch):
    """Strip every FraudGuard variable so defaults can be asserted."""
    for key in list(os.environ):
        if key.split("_")[0] in {
            "OS",
            "OTX",
            "MISTRAL",
            "GOOGLE",
            "PROGRAMMABLE",
            "POSTGRES",
            "AWS",
            "KAFKA",
            "PW",
        }:
            monkeypatch.delenv(key, raising=False)
    from fraudguard import config

    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()
