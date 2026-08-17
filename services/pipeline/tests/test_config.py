from __future__ import annotations

import pytest

from fraudguard.config import ConfigError, get_settings, require


class TestKafkaSettings:
    def test_each_flow_gets_its_own_consumer_group(self, isolated_settings):
        """Regression: every flow used group.id=0 and stole each other's partitions."""
        kafka = isolated_settings.kafka
        assert kafka.rdkafka(group_suffix="kyc")["group.id"] != (
            kafka.rdkafka(group_suffix="db-sink")["group.id"]
        )

    def test_rdkafka_has_the_keys_pathway_expects(self, isolated_settings):
        settings = isolated_settings.kafka.rdkafka()
        assert set(settings) == {
            "bootstrap.servers",
            "group.id",
            "session.timeout.ms",
            "auto.offset.reset",
        }


class TestPostgresSettings:
    def test_dsn_is_well_formed(self, isolated_settings):
        assert isolated_settings.postgres.dsn.startswith("postgresql://test:test@localhost:5432/")

    def test_connection_parts_require_a_password(self, isolated_settings, monkeypatch):
        from fraudguard import config

        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
        config.get_settings.cache_clear()
        with pytest.raises(ConfigError, match="POSTGRES_PASSWORD"):
            _ = config.get_settings().postgres.connection_parts

    def test_accepts_either_dbname_variable(self, isolated_settings, monkeypatch):
        """POSTGRES_DBNAME and POSTGRES_DB were both used across the old modules."""
        from fraudguard import config

        monkeypatch.delenv("POSTGRES_DBNAME", raising=False)
        monkeypatch.setenv("POSTGRES_DB", "alt_db")
        config.get_settings.cache_clear()
        assert config.get_settings().postgres.dbname == "alt_db"


class TestSearchKeys:
    def test_collects_matching_pairs(self, isolated_settings, monkeypatch):
        from fraudguard import config

        monkeypatch.setenv("GOOGLE_CLOUD_API_KEY_1", "key-1")
        monkeypatch.setenv("PROGRAMMABLE_SEARCH_ENGINE_ID_1", "cx-1")
        monkeypatch.setenv("GOOGLE_CLOUD_API_KEY_2", "key-2")
        monkeypatch.setenv("PROGRAMMABLE_SEARCH_ENGINE_ID_2", "cx-2")
        config.get_settings.cache_clear()
        assert config.get_settings().enrichment.google_search_keys == (
            ("key-1", "cx-1"),
            ("key-2", "cx-2"),
        )

    def test_a_gap_does_not_truncate_the_pool(self, isolated_settings, monkeypatch):
        """Regression: the old loop stopped at the first missing index."""
        from fraudguard import config

        monkeypatch.setenv("GOOGLE_CLOUD_API_KEY_1", "key-1")
        monkeypatch.setenv("PROGRAMMABLE_SEARCH_ENGINE_ID_1", "cx-1")
        # index 2 deliberately absent
        monkeypatch.setenv("GOOGLE_CLOUD_API_KEY_3", "key-3")
        monkeypatch.setenv("PROGRAMMABLE_SEARCH_ENGINE_ID_3", "cx-3")
        config.get_settings.cache_clear()
        keys = config.get_settings().enrichment.google_search_keys
        assert ("key-3", "cx-3") in keys

    def test_unpaired_key_is_ignored(self, isolated_settings, monkeypatch):
        from fraudguard import config

        monkeypatch.setenv("GOOGLE_CLOUD_API_KEY_4", "orphan")
        monkeypatch.delenv("PROGRAMMABLE_SEARCH_ENGINE_ID_4", raising=False)
        config.get_settings.cache_clear()
        keys = config.get_settings().enrichment.google_search_keys
        assert all(key != "orphan" for key, _ in keys)


class TestPaths:
    def test_directories_are_created(self, isolated_settings):
        for directory in (
            isolated_settings.paths.out,
            isolated_settings.paths.state,
            isolated_settings.paths.logs,
        ):
            assert directory.is_dir()


class TestRequire:
    def test_reports_every_missing_key_at_once(self, isolated_settings, monkeypatch):
        monkeypatch.delenv("OS_API_KEY", raising=False)
        monkeypatch.delenv("MISTRAL_KEY", raising=False)
        with pytest.raises(ConfigError) as excinfo:
            require(isolated_settings, ["OS_API_KEY", "MISTRAL_KEY"])
        message = str(excinfo.value)
        assert "OS_API_KEY" in message
        assert "MISTRAL_KEY" in message

    def test_passes_when_everything_is_present(self, isolated_settings):
        require(isolated_settings, ["OS_API_KEY", "POSTGRES_PASSWORD"])


class TestCaching:
    def test_settings_are_a_singleton(self, isolated_settings):
        assert get_settings() is get_settings()
