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
    redis_url: str = "redis://localhost:6379/0"

    # --- Security ------------------------------------------------------
    # Required: the process refuses to start without it rather than falling back
    # to a guessable default.
    jwt_secret: str = Field(min_length=8, description="HMAC signing key for access tokens")
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
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

    # --- Object storage / cloud ----------------------------------------
    aws_region: str | None = None
    s3_bucket: str | None = None

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
