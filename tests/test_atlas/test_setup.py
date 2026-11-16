"""Configuration checks behind ``atlas doctor`` (``atlas_eng.setup``)."""

from pathlib import Path

import pytest

from atlas_eng import setup
from atlas_eng.setup import CheckStatus, ConfigurationReport, diagnose

_ATLAS_VARIABLES = (
    "ATLAS_AI_PROTOCOL",
    "ATLAS_AI_MODEL",
    "ATLAS_AI_ENDPOINT",
    "ATLAS_AI_API_KEY",
    "ATLAS_GEMINI_API_KEY",
    "ATLAS_GEMINI_MODEL",
    "ATLAS_WORKSPACE_ROOT",
    "ATLAS_EMBEDDING_ENABLED",
    "ATLAS_EMBEDDING_PROTOCOL",
    "ATLAS_EMBEDDING_MODEL",
)


@pytest.fixture(autouse=True)
def clean_configuration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Run every check from an empty directory with no ATLAS_* variables."""
    for name in _ATLAS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


def _status(report: ConfigurationReport, name: str) -> CheckStatus:
    return next(check.status for check in report.checks if check.name == name)


def _check(report: ConfigurationReport, name: str) -> setup.ConfigurationCheck:
    return next(check for check in report.checks if check.name == name)


def test_complete_configuration_is_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_AI_PROTOCOL", "OLLAMA")
    monkeypatch.setenv("ATLAS_AI_MODEL", "llama3")

    report = diagnose()

    assert report.ok
    assert _status(report, "Protocol settings") == CheckStatus.OK
    assert _status(report, "Config file") == CheckStatus.WARN


def test_settings_come_from_the_nearest_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text(
        "ATLAS_AI_PROTOCOL=ANTHROPIC\nATLAS_AI_API_KEY=k\nATLAS_AI_MODEL=m\n",
        encoding="utf-8",
    )
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)

    monkeypatch.chdir(nested)
    report = diagnose()

    assert report.ok
    assert _check(report, "Config file").detail.endswith(".env")
    assert "ANTHROPIC" in _check(report, "AI protocol").detail


def test_missing_extra_fails_with_the_install_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATLAS_AI_PROTOCOL", "GEMINI")
    monkeypatch.setenv("ATLAS_GEMINI_API_KEY", "k")
    monkeypatch.setenv("ATLAS_GEMINI_MODEL", "m")
    monkeypatch.setattr(setup, "extra_installed", lambda _setup: False)

    report = diagnose()

    assert not report.ok
    assert "atlas-eng[gemini]" in _check(report, "Protocol package").fix


def test_unwritable_workspace_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ATLAS_AI_PROTOCOL", "SCRIPTED")
    monkeypatch.setenv("ATLAS_WORKSPACE_ROOT", str(tmp_path / "ws"))
    monkeypatch.setattr("os.access", lambda _path, _mode: False)

    report = diagnose()

    assert _status(report, "Workspace") == CheckStatus.FAIL


def test_misconfigured_embeddings_only_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_AI_PROTOCOL", "SCRIPTED")
    monkeypatch.setenv("ATLAS_EMBEDDING_ENABLED", "true")
    monkeypatch.setenv("ATLAS_EMBEDDING_PROTOCOL", "ANTHROPIC")

    report = diagnose()

    assert report.ok
    assert _status(report, "Semantic retrieval") == CheckStatus.WARN


def test_working_embeddings_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_AI_PROTOCOL", "SCRIPTED")
    monkeypatch.setenv("ATLAS_EMBEDDING_ENABLED", "true")

    assert _status(diagnose(), "Semantic retrieval") == CheckStatus.OK


def test_langfuse_keys_without_package_warn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ATLAS_AI_PROTOCOL", "SCRIPTED")
    (tmp_path / ".env").write_text(
        "LANGFUSE_PUBLIC_KEY=pk\nLANGFUSE_SECRET_KEY=sk\n", encoding="utf-8"
    )
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)

    report = diagnose()

    assert _status(report, "Langfuse tracing") == CheckStatus.WARN


def test_live_check_runs_only_when_everything_else_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATLAS_AI_PROTOCOL", "ANTHROPIC")  # no key: fails offline

    report = diagnose(live=True)

    assert not any(check.name == "Live request" for check in report.checks)


def test_live_check_succeeds_against_the_scripted_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATLAS_AI_PROTOCOL", "SCRIPTED")

    report = diagnose(live=True)

    assert _status(report, "Live request") == CheckStatus.OK


def test_render_env_file_comments_out_unset_values() -> None:
    gemini = setup.protocol_setup("gemini")
    assert gemini is not None

    text = setup.render_env_file(gemini, {"ATLAS_GEMINI_MODEL": "m"})

    assert "ATLAS_AI_PROTOCOL=GEMINI" in text
    assert 'ATLAS_GEMINI_MODEL="m"' in text
    assert "# ATLAS_GEMINI_API_KEY=" in text


def test_every_factory_protocol_has_a_setup_entry() -> None:
    """A protocol added to the factory must also be explained to new users."""
    from atlas_eng.engine.ai.factory import ProtocolFactory  # noqa: PLC0415

    registered = set(ProtocolFactory()._registry)
    described = {protocol.name for protocol in setup.PROTOCOLS}

    assert registered == described
