"""Configuration settings for the ATLAS platform using Pydantic Settings."""

from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Execution environment for the ATLAS platform."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """ATLAS application settings, loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_prefix="ATLAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment (development, testing, production)",
    )

    debug: bool = Field(
        default=False,
        description="Enable debug logging and verbose error outputs",
    )

    workspace_root: Path = Field(
        default=Path("./workspace"),
        description="Path to the active engineering workspace",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )


def get_settings() -> Settings:
    """Load and return the ATLAS settings.

    Uses Pydantic Settings to load from environment variables and the .env file.
    Using a getter function facilitates mock injection during testing.

    Returns:
        Settings: Loaded configuration settings.
    """
    return Settings()
