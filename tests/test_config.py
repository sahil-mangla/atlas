from pathlib import Path

from engine.config import Environment, Settings, get_settings


def test_settings_default_values() -> None:
    """Verify that default settings are loaded correctly."""
    settings = get_settings()
    assert settings.environment == Environment.DEVELOPMENT


def test_settings_default_ai_timeout_seconds() -> None:
    """Verify the AI protocol HTTP timeout defaults to 60 seconds."""
    settings = get_settings()
    assert settings.ai_timeout_seconds == 60


def test_settings_environ_override() -> None:
    """Verify that Settings supports loading values via the constructor.

    This ensures Pydantic validation is functional and allows dependency
    injection without direct access to os.environ.
    """
    settings = Settings(
        environment=Environment.PRODUCTION,
        workspace_root=Path("/custom/path"),
    )
    assert settings.environment == Environment.PRODUCTION
    assert str(settings.workspace_root) == "/custom/path"


def test_settings_via_env_file(tmp_path: Path) -> None:
    """Verify that settings can load from an env file.

    This tests the Pydantic Settings integration without accessing os.environ.
    """
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "ATLAS_ENVIRONMENT=production\nATLAS_WORKSPACE_ROOT=/custom/path\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)  # type: ignore[call-arg]

    assert settings.environment == Environment.PRODUCTION
    assert str(settings.workspace_root) == "/custom/path"
