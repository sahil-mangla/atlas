"""Configuration settings for the ATLAS platform using Pydantic Settings."""

import logging
from enum import StrEnum
from pathlib import Path

from dotenv import find_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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

    workspace_root: Path = Field(
        default=Path("./workspace"),
        description="Path to the active engineering workspace",
    )

    gemini_api_key: str | None = Field(
        default=None, description="API key used by the Gemini provider."
    )
    gemini_model: str | None = Field(
        default=None, description="Gemini model name used for prompt execution."
    )
    ai_protocol: str = Field(default="GEMINI", description="Configured AI protocol.")
    ai_endpoint: str | None = Field(default=None, description="AI protocol endpoint.")
    ai_model: str | None = Field(default=None, description="AI protocol model.")
    ai_api_key: str | None = Field(default=None, description="AI protocol credential.")
    ai_timeout_seconds: int = Field(
        default=60, description="AI protocol HTTP request timeout, in seconds."
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )

    research_max_candidates: int = Field(
        default=5,
        description="Max paper candidates kept per research proposal generation.",
    )
    research_retrieval_timeout_seconds: int = Field(
        default=15,
        description="HTTP timeout, in seconds, per paper-source API call.",
    )


def get_settings() -> Settings:
    """Load and return the ATLAS settings.

    Uses Pydantic Settings to load from environment variables and the .env file.
    Using a getter function facilitates mock injection during testing.

    The bare ``env_file=".env"`` in ``model_config`` only ever looked in the
    current process's CWD, so running Atlas from any subdirectory silently
    lost the project's .env (and thus workspace_root) with no diagnostic --
    just a downstream "not found" error. Resolve upward from CWD instead, and
    log what was actually resolved so a misconfigured invocation is
    diagnosable rather than alarming.

    Returns:
        Settings: Loaded configuration settings.
    """
    env_path = find_dotenv(usecwd=True)
    settings = Settings(_env_file=env_path or None)  # type: ignore[call-arg]
    logger.info(
        "ATLAS config resolved: env_file=%s workspace_root=%s",
        env_path or "<not found>",
        settings.workspace_root.resolve(),
    )
    return settings
