"""Interactive ``atlas init``: prompts, secret handling and file contents."""

import io
from pathlib import Path

from atlas_eng.clients.cli.commands import InitCommand
from atlas_eng.clients.cli.onboarding import run_init


def _answers(*values: str):  # type: ignore[no-untyped-def]
    queue = list(values)
    asked: list[str] = []

    def ask(prompt: str) -> str:
        asked.append(prompt)
        return queue.pop(0)

    return ask, asked


def test_interactive_init_reads_the_key_without_echo(tmp_path: Path) -> None:
    ask, asked = _answers("2", "")  # ANTHROPIC, accept default model
    secret, secret_asked = _answers("sk-ant-secret")

    run_init(InitCommand(), cwd=tmp_path, out=io.StringIO(), ask=ask, ask_secret=secret)

    env_file = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "ATLAS_AI_PROTOCOL=ANTHROPIC" in env_file
    assert 'ATLAS_AI_API_KEY="sk-ant-secret"' in env_file
    assert 'ATLAS_AI_MODEL="claude-opus-5-5"' in env_file
    assert len(secret_asked) == 1
    assert "API key" in secret_asked[0]
    assert not any("API key" in prompt for prompt in asked)


def test_protocol_can_be_chosen_by_name_and_retries_bad_input(tmp_path: Path) -> None:
    out = io.StringIO()
    ask, _ = _answers("nine", "ollama", "", "llama3")

    run_init(InitCommand(), cwd=tmp_path, out=out, ask=ask, ask_secret=ask)

    assert "Please enter one of the numbers" in out.getvalue()
    env_file = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "ATLAS_AI_PROTOCOL=OLLAMA" in env_file
    assert 'ATLAS_AI_MODEL="llama3"' in env_file


def test_unanswered_required_values_are_listed(tmp_path: Path) -> None:
    ask, _ = _answers("", "")

    message = run_init(
        InitCommand(protocol="GEMINI"),
        cwd=tmp_path,
        out=io.StringIO(),
        ask=ask,
        ask_secret=ask,
    )

    assert "Still to fill in: ATLAS_GEMINI_API_KEY, ATLAS_GEMINI_MODEL" in message
    env_file = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "# ATLAS_GEMINI_API_KEY=" in env_file


def test_values_with_quotes_round_trip_through_dotenv(tmp_path: Path) -> None:
    from dotenv import dotenv_values  # noqa: PLC0415

    ask, _ = _answers("", 'weird "model" name')  # default endpoint, then model
    run_init(
        InitCommand(protocol="OLLAMA"),
        cwd=tmp_path,
        out=io.StringIO(),
        ask=ask,
        ask_secret=ask,
    )

    assert dotenv_values(tmp_path / ".env")["ATLAS_AI_MODEL"] == 'weird "model" name'
