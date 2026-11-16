"""Optional Langfuse tracing: off by default, on only with keys and the package."""

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from atlas_eng.shared.observability import tracing

REPO_ROOT = Path(__file__).resolve().parents[2]
# Captured at import, before the suite-wide fixture in tests/conftest.py
# replaces it to keep a developer's own .env out of the tests.
_REAL_DOTENV_LOADER = tracing._load_keys_from_dotenv


@pytest.fixture(autouse=True)
def fresh_decision(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Each test decides afresh, from a directory with no .env file."""
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    tracing.reset()
    yield
    tracing.reset()


def test_disabled_without_keys() -> None:
    assert not tracing.is_enabled()


def test_enabled_with_keys_in_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")

    assert tracing.is_enabled()


def test_keys_are_read_from_the_project_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tracing, "_load_keys_from_dotenv", _REAL_DOTENV_LOADER)
    (tmp_path / ".env").write_text(
        "LANGFUSE_PUBLIC_KEY=pk\nLANGFUSE_SECRET_KEY=sk\n", encoding="utf-8"
    )

    assert tracing.is_enabled()


def test_keys_without_the_package_warn_and_stay_disabled(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)

    assert not tracing.is_enabled()
    assert "atlas-eng[langfuse]" in caplog.text


def test_disabled_decorator_calls_through_and_drops_langfuse_kwargs() -> None:
    calls: list[dict[str, Any]] = []

    @tracing.observe(name="x")
    def traced(value: int, **kwargs: Any) -> int:
        calls.append(kwargs)
        return value * 2

    assert traced(21, langfuse_observation_id="abc", keep="me") == 42
    assert calls == [{"keep": "me"}]


def test_disabled_helpers_are_no_ops() -> None:
    tracing.update_current_observation(output="x")
    tracing.update_current_trace(name="x")

    assert tracing.get_current_trace_id() is None


def test_enabled_decorator_delegates_to_langfuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    seen: list[dict[str, Any]] = []

    def fake_observe(**options: Any) -> Any:
        seen.append(options)

        def decorate(function: Any) -> Any:
            return lambda *args, **kwargs: ("traced", function(*args, **kwargs))

        return decorate

    import langfuse.decorators  # noqa: PLC0415 - patched just for this test

    monkeypatch.setattr(langfuse.decorators, "observe", fake_observe)

    @tracing.observe(name="op", as_type="generation")
    def traced() -> str:
        return "ok"

    assert traced() == ("traced", "ok")  # type: ignore[comparison-overlap]
    assert seen == [{"name": "op", "as_type": "generation"}]


def test_langfuse_is_never_imported_without_keys(tmp_path: Path) -> None:
    """Importing every traced module, and running a traced call, stays silent."""
    script = (
        "import sys\n"
        "import atlas_eng\n"
        "import atlas_eng.engine.ai.adapters.ollama as ollama\n"
        "import atlas_eng.engine.ai.adapters.gemini as gemini\n"
        "from atlas_eng.shared.observability import tracing\n"
        "tracing.update_current_observation(output='x')\n"
        "print('langfuse' in sys.modules, 'google.genai' in sys.modules)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={"PATH": "", "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout.split() == ["False", "False"]
    assert completed.stderr == ""
