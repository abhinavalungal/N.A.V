"""Configuration behaviour."""

from __future__ import annotations

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
