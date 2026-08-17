"""Unit tests for the cross-cutting core modules.

None of these need a database, a network or credentials — they cover the parts
where a regression would silently weaken security or change every response
shape.
"""

from __future__ import annotations

import pytest

from app.core import config


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/test")
    monkeypatch.setenv("SECRET_KEY", "0" * 64)
    config.get_settings.cache_clear()
    yield config.get_settings()
    config.get_settings.cache_clear()


class TestConfig:
    def test_assembles_the_database_url_from_postgres_variables(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("POSTGRES_HOST", "db.internal")
        monkeypatch.setenv("POSTGRES_PASSWORD", "hunter2")
        monkeypatch.setenv("POSTGRES_DB", "values_db")
        monkeypatch.setenv("SECRET_KEY", "0" * 64)
        config.get_settings.cache_clear()
        assert config.get_settings().database.url == (
            "postgresql://user:hunter2@db.internal:5432/values_db"
        )
        config.get_settings.cache_clear()

    def test_missing_database_configuration_is_a_clear_error(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
        config.get_settings.cache_clear()
        with pytest.raises(config.ConfigurationError, match="DATABASE_URL"):
            config.get_settings()
        config.get_settings.cache_clear()

    def test_placeholder_secret_is_refused_in_production(self, monkeypatch):
        """Regression: the placeholder key was the committed default."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/test")
        monkeypatch.setenv(
            "SECRET_KEY", "your-secret-key-change-this-in-production-use-openssl-rand-hex-32"
        )
        config.get_settings.cache_clear()
        with pytest.raises(config.ConfigurationError, match="SECRET_KEY"):
            config.get_settings()
        config.get_settings.cache_clear()

    def test_development_generates_a_secret_and_warns(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/test")
        monkeypatch.delenv("SECRET_KEY", raising=False)
        config.get_settings.cache_clear()
        settings = config.get_settings()
        assert settings.security.generated_secret is True
        assert any("SECRET_KEY" in warning for warning in settings.warnings)
        config.get_settings.cache_clear()

    def test_wildcard_cors_is_refused_in_production(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/test")
        monkeypatch.setenv("SECRET_KEY", "0" * 64)
        monkeypatch.setenv("CORS_ORIGINS", "*")
        config.get_settings.cache_clear()
        with pytest.raises(config.ConfigurationError, match="CORS_ORIGINS"):
            config.get_settings()
        config.get_settings.cache_clear()

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ('["http://a", "http://b"]', ["http://a", "http://b"]),
            ("http://a,http://b", ["http://a", "http://b"]),
            ("http://a", ["http://a"]),
        ],
    )
    def test_cors_accepts_json_and_csv(self, monkeypatch, raw, expected):
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/test")
        monkeypatch.setenv("SECRET_KEY", "0" * 64)
        monkeypatch.setenv("CORS_ORIGINS", raw)
        config.get_settings.cache_clear()
        assert config.get_settings().cors_origins == expected
        config.get_settings.cache_clear()


class TestPagination:
    def test_limit_is_capped_at_the_configured_maximum(self, settings):
        from app.core.pagination import page_params

        params = page_params(offset=0, limit=100_000, skip=None)
        assert params.limit == settings.max_page_size

    def test_deprecated_skip_still_works(self, settings):
        from app.core.pagination import page_params

        assert page_params(offset=0, limit=10, skip=40).offset == 40

    def test_offset_wins_over_skip(self, settings):
        from app.core.pagination import page_params

        assert page_params(offset=20, limit=10, skip=40).offset == 20

    def test_has_more_is_computed_from_the_total(self, settings):
        from app.core.pagination import Page, PageParams

        page = Page.build([1, 2, 3], total=10, params=PageParams(offset=0, limit=3))
        assert page.has_more is True
        last = Page.build([1], total=4, params=PageParams(offset=3, limit=3))
        assert last.has_more is False


class TestRateLimiter:
    def test_allows_up_to_the_limit_then_blocks(self):
        from app.core.middleware import RateLimiter

        limiter = RateLimiter(per_minute=3)
        assert all(limiter.allow("client")[0] for _ in range(3))
        allowed, retry_after = limiter.allow("client")
        assert allowed is False
        assert retry_after > 0

    def test_clients_are_independent(self):
        from app.core.middleware import RateLimiter

        limiter = RateLimiter(per_minute=1)
        assert limiter.allow("a")[0] is True
        assert limiter.allow("b")[0] is True
        assert limiter.allow("a")[0] is False

    def test_zero_disables_limiting(self):
        from app.core.middleware import RateLimiter

        limiter = RateLimiter(per_minute=0)
        assert all(limiter.allow("client")[0] for _ in range(100))


class TestErrors:
    def test_every_error_maps_to_its_status_code(self):
        from app.core import errors

        assert errors.NotFoundError("x").status_code == 404
        assert errors.ConflictError("x").status_code == 409
        assert errors.AuthenticationError("x").status_code == 401
        assert errors.AuthorizationError("x").status_code == 403
        assert errors.UpstreamError("x").status_code == 502

    def test_error_payload_shape_is_stable(self, settings):
        import json

        from app.core.errors import error_response

        payload = json.loads(error_response(404, "not_found", "gone").body)
        assert set(payload) == {"error", "request_id"}
        assert set(payload["error"]) == {"code", "message", "details"}
