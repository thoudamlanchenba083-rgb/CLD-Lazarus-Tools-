"""
brAInfection V2 — Application configuration.

Loads settings from environment variables (or .env file).
"""
import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    env: str = Field(default="dev", alias="ENV")

    # Admin token (V1 compatibility — will be replaced by proper login in Phase 10)
    admin_token: str = Field(default="change-this-local-demo-token", alias="ADMIN_TOKEN")

    # Database
    database_url: str = Field(
        default="sqlite:///./data/brAInfection.db",
        alias="DATABASE_URL",
    )

    # Secret key for generating session tokens
    secret_key: str = Field(default="change-this-to-a-random-secret-key", alias="SECRET_KEY")

    # Session lifetime in minutes
    session_lifetime_minutes: int = Field(default=30, alias="SESSION_LIFETIME_MINUTES")

    # Data retention in days
    retention_days: int = Field(default=30, alias="RETENTION_DAYS")

    # CORS origins (comma-separated string)
    cors_origins: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000",
        alias="CORS_ORIGINS",
    )

    # Consent version — bump when wording changes
    consent_version: int = 1

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.env.lower() == "dev"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
