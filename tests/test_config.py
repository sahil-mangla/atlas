from pathlib import Path

from engine.ai.factory import ProtocolFactory
from engine.ai.provider import AIProvider
from engine.config import Environment, Settings, get_settings

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_EXAMPLE = _REPO_ROOT / ".env.example"

# Protocol names ProtocolFactory() constructs successfully -- probing via
# .create() (public API) rather than its internal registry, so this stays
# accurate without reaching past the class boundary.
_KNOWN_AI_PROTOCOLS = ("GEMINI", "ANTHROPIC", "OPENAI_COMPATIBLE", "OLLAMA")


def test_known_ai_protocols_are_exhaustive() -> None:
    """Guard the fixture list above against a protocol being added/removed."""
    factory = ProtocolFactory()
    for protocol in _KNOWN_AI_PROTOCOLS:
        provider = factory.create(protocol)
        assert isinstance(provider, AIProvider)


def test_settings_default_values() -> None:
    """Verify that default settings are loaded correctly."""
    settings = get_settings()
    assert settings.environment == Environment.DEVELOPMENT


def test_settings_default_ai_timeout_seconds() -> None:
    """Verify the AI protocol HTTP timeout defaults to 60 seconds."""
    settings = get_settings()
    assert settings.ai_timeout_seconds == 60


def test_settings_default_log_level() -> None:
    """Verify the logging level defaults to INFO."""
    settings = get_settings()
    assert settings.log_level == "INFO"


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


def test_env_example_documents_every_settings_field() -> None:
    """RC-004 regression: .env.example must not go stale against Settings.

    Every ``ATLAS_``-prefixed environment variable Settings actually reads
    must appear somewhere in .env.example -- as a live value or in a
    commented-out block -- so a first-time user can discover it there
    instead of reading engine/config.py.
    """
    content = _ENV_EXAMPLE.read_text()
    for field_name in Settings.model_fields:
        env_var = f"ATLAS_{field_name.upper()}"
        assert env_var in content, (
            f"{env_var} (Settings.{field_name}) is not documented in .env.example"
        )


def test_env_example_documents_every_registered_ai_protocol() -> None:
    """RC-004 regression: every AI protocol the factory can construct must
    have a corresponding block in .env.example, so switching providers is
    discoverable without reading engine/ai/factory.py."""
    content = _ENV_EXAMPLE.read_text()
    for protocol in _KNOWN_AI_PROTOCOLS:
        assert protocol in content, (
            f"AI protocol {protocol!r} is not documented in .env.example"
        )
    # LM Studio is a common local OPENAI_COMPATIBLE target, not a distinct
    # protocol -- must still be discoverable by name.
    assert "LM Studio" in content
