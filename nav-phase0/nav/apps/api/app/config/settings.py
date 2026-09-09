"""Environment-driven application settings.

No secret, credential or endpoint is ever hard-coded in source. Everything is
read from the environment (see .env.example at the repository root).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]


class Settings(BaseSettings):
    """Runtime configuration for the N.A.V. API and workers."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---------------------------------------------------
    app_name: str = "N.A.V."
    app_full_name: str = "Nautical Agentic Navigator"
    app_version: str = "0.1.0"
    app_env: Environment = "local"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # --- Datastores ----------------------------------------------------
    database_url: str = "postgresql+asyncpg://nav:nav@localhost:5432/nav"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_echo: bool = False

    # Optional. Nothing in the prototype queues work, so an instance without
    # Redis is a valid deployment rather than a broken one. Required from
    # Phase 4, when optimisation runs move onto the worker.
    redis_url: str | None = None

    # --- Security ------------------------------------------------------
    # Authentication arrives in Phase 1. Until there is something to sign,
    # there is no key to configure and nothing to leave insecurely defaulted.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Comma-separated list in the environment.",
    )

    # --- Providers (all default to mock so the stack runs offline) ------
    llm_provider: Literal["mock", "ollama", "openai", "anthropic"] = "mock"
    llm_model: str = "mock-model"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    weather_provider: Literal["mock", "open_meteo"] = "mock"
    routing_provider: Literal["mock", "searoute"] = "mock"
    weather_api_key: str | None = None
    routing_api_key: str | None = None

    # --- Agent guardrails (enforced from Phase 5) -----------------------
    agent_max_tool_calls: int = 20
    agent_max_iterations: int = 8
    agent_timeout_seconds: int = 120
    nav_agent_prompt_version: str = "1.0.0"

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalise_database_url(cls, value: object) -> object:
        """Accept the connection strings managed platforms hand out.

        Render, Heroku, Fly and friends supply `postgres://` or
        `postgresql://`, which SQLAlchemy would route to psycopg. The async
        engine needs the asyncpg driver, and asyncpg takes `ssl` rather than
        libpq's `sslmode`.
        """
        if not isinstance(value, str):
            return value
        for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
            if value.startswith(prefix):
                return value
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                value = "postgresql+asyncpg://" + value[len(prefix) :]
                break
        return value.replace("?sslmode=", "?ssl=").replace("&sslmode=", "&ssl=")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept either a real list or a comma-separated environment string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def redis_configured(self) -> bool:
        return bool(self.redis_url)

    @property
    def mock_providers(self) -> list[str]:
        """Providers currently answering with mock data, for honest UI labelling."""
        mocked: list[str] = []
        if self.llm_provider == "mock":
            mocked.append("llm")
        if self.weather_provider == "mock":
            mocked.append("weather")
        if self.routing_provider == "mock":
            mocked.append("routing")
        return mocked


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
