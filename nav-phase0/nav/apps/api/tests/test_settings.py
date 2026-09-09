"""Configuration behaviour."""

from __future__ import annotations

import pytest

from app.config.settings import Settings


def test_cors_origins_accepts_comma_separated_string() -> None:
    settings = Settings(cors_origins="http://a.test, http://b.test")  # type: ignore[arg-type]

    assert settings.cors_origins == ["http://a.test", "http://b.test"]


def test_providers_default_to_mock_so_the_stack_runs_offline() -> None:
    settings = Settings()

    assert settings.llm_provider == "mock"
    assert settings.weather_provider == "mock"
    assert settings.routing_provider == "mock"
    assert set(settings.mock_providers) == {"llm", "weather", "routing"}


def test_configured_provider_is_no_longer_listed_as_mock() -> None:
    settings = Settings(llm_provider="ollama", llm_base_url="http://localhost:11434")

    assert "llm" not in settings.mock_providers
    assert set(settings.mock_providers) == {"weather", "routing"}


def test_no_secret_is_baked_into_the_defaults() -> None:
    settings = Settings()

    assert settings.llm_api_key is None
    assert settings.weather_api_key is None
    assert settings.routing_api_key is None


def test_settings_load_with_an_empty_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """A prototype has to start with no configuration at all."""
    for key in ("APP_ENV", "DATABASE_URL", "REDIS_URL", "CORS_ORIGINS"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.app_env == "local"
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.redis_url is None
    assert settings.cors_origins == ["http://localhost:3000"]


def test_redis_is_optional() -> None:
    """Nothing queues work yet, so an instance without Redis is valid."""
    assert Settings(redis_url=None).redis_configured is False
    assert Settings(redis_url="redis://localhost:6379/0").redis_configured is True


def test_managed_platform_url_is_routed_to_asyncpg() -> None:
    """Render and Heroku hand out libpq-style URLs; the async engine needs asyncpg."""
    settings = Settings(database_url="postgresql://nav:pw@dpg-abc.oregon-postgres.render.com/nav")

    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert "nav:pw@dpg-abc.oregon-postgres.render.com/nav" in settings.database_url


def test_legacy_postgres_scheme_is_accepted() -> None:
    settings = Settings(database_url="postgres://nav:pw@host/nav")

    assert settings.database_url == "postgresql+asyncpg://nav:pw@host/nav"


def test_sslmode_is_translated_for_asyncpg() -> None:
    """asyncpg takes `ssl`; passing libpq's `sslmode` through would raise."""
    settings = Settings(database_url="postgresql://nav:pw@host/nav?sslmode=require")

    assert settings.database_url.endswith("?ssl=require")
    assert "sslmode" not in settings.database_url


def test_explicit_asyncpg_url_is_left_alone() -> None:
    settings = Settings(database_url="postgresql+asyncpg://nav:nav@localhost:5432/nav")

    assert settings.database_url == "postgresql+asyncpg://nav:nav@localhost:5432/nav"
