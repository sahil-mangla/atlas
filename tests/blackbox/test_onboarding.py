"""Black-box tests for the first-run commands: demo, init and doctor."""

import subprocess
from pathlib import Path

import pytest

from tests.blackbox.conftest import Cli


def test_demo_runs_offline_whatever_the_configuration(cli: Cli) -> None:
    # A configured real provider must not be used by the demo.
    result = cli.ok("demo", env={"ATLAS_AI_PROTOCOL": "GEMINI"})

    for stage in ("research", "planning", "architecture", "review"):
        assert f"[{stage}] Proposal drafted:" in result.stdout
    assert "engineering-knowledge candidates" in result.stdout
    assert not (cli.cwd / "workspace").exists(), "demo wrote to the user workspace"
    assert cli.network_attempts() == []


def test_demo_output_points_at_a_readable_record(cli: Cli) -> None:
    result = cli.ok("demo")

    line = next(
        line for line in result.stdout.splitlines() if "Readable proposals:" in line
    )
    approved = line.split("Readable proposals:", 1)[1].strip()
    assert len(list(Path(approved).iterdir())) == 4


def test_init_writes_an_env_that_doctor_accepts(cli: Cli) -> None:
    result = cli.ok("init", "--protocol", "OLLAMA", "--model", "qwen2.5-coder:7b")

    env_file = (cli.cwd / ".env").read_text(encoding="utf-8")
    assert "ATLAS_AI_PROTOCOL=OLLAMA" in env_file
    assert 'ATLAS_AI_MODEL="qwen2.5-coder:7b"' in env_file
    assert "atlas doctor" in result.stdout
    # With nothing in the environment, the .env just written decides.
    doctor = cli.ok("doctor", env={"ATLAS_AI_PROTOCOL": None})
    assert "OLLAMA" in doctor.stdout
    assert "Ready." in doctor.stdout


def test_init_never_overwrites_without_force_and_keeps_a_backup(cli: Cli) -> None:
    env_path = cli.cwd / ".env"
    env_path.write_text("ATLAS_AI_API_KEY=keep-me\n", encoding="utf-8")

    refused = cli("init", "--protocol", "SCRIPTED")
    assert refused.returncode != 0
    assert "already exists" in refused.output
    assert env_path.read_text(encoding="utf-8") == "ATLAS_AI_API_KEY=keep-me\n"

    cli.ok("init", "--protocol", "SCRIPTED", "--force")
    assert "ATLAS_AI_PROTOCOL=SCRIPTED" in env_path.read_text(encoding="utf-8")
    backup = (cli.cwd / ".env.bak").read_text(encoding="utf-8")
    assert backup == "ATLAS_AI_API_KEY=keep-me\n"


def test_init_without_a_terminal_needs_the_protocol_flag(cli: Cli) -> None:
    result = cli("init")

    assert result.returncode != 0
    assert "--protocol" in result.output
    assert not (cli.cwd / ".env").exists()


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True, check=False).returncode
    != 0,
    reason="git is not installed",
)
def test_init_warns_when_env_is_not_git_ignored(cli: Cli) -> None:
    subprocess.run(["git", "init", "-q", str(cli.cwd)], check=True)

    warned = cli.ok("init", "--protocol", "SCRIPTED")
    assert "not ignored by git" in warned.stdout

    (cli.cwd / ".gitignore").write_text(".env\n.env.bak\n", encoding="utf-8")
    quiet = cli.ok("init", "--protocol", "SCRIPTED", "--force")
    assert "not ignored by git" not in quiet.stdout


def test_doctor_reports_missing_settings_and_fails(cli: Cli) -> None:
    result = cli("doctor", env={"ATLAS_AI_PROTOCOL": "ANTHROPIC"})

    assert result.returncode == 1
    assert "ATLAS_AI_API_KEY" in result.stdout
    assert "Traceback" not in result.output


def test_doctor_works_even_when_the_platform_cannot_start(cli: Cli) -> None:
    """An unknown protocol stops every other command; doctor must explain it."""
    broken = cli("project", "list", env={"ATLAS_AI_PROTOCOL": "BOGUS"})
    assert broken.returncode != 0

    result = cli("doctor", env={"ATLAS_AI_PROTOCOL": "BOGUS"})

    assert result.returncode == 1
    assert "Unknown protocol 'BOGUS'" in result.stdout
    assert "SCRIPTED" in result.stdout


def test_doctor_live_sends_one_request_through_the_provider(cli: Cli) -> None:
    result = cli.ok("doctor", "--live")

    assert "Live request" in result.stdout
    assert "valid structured response" in result.stdout
    assert cli.network_attempts() == []


def test_doctor_live_reports_a_provider_failure(cli: Cli) -> None:
    result = cli("doctor", "--live", env={"ATLAS_AI_MODEL": "malformed-json"})

    assert result.returncode == 1
    assert "Live request" in result.stdout
    assert "Traceback" not in result.output


def test_version_and_help_do_not_start_the_platform(cli: Cli) -> None:
    """Both must work with a configuration that would stop the platform."""
    env = {"ATLAS_AI_PROTOCOL": "BOGUS"}

    assert cli.ok("--version", env=env).stdout.startswith("ATLAS")
    assert "Getting started" in cli.ok("--help", env=env).stdout
    assert not (cli.cwd / "workspace").exists()


def test_a_whole_stage_without_typing_a_single_id(cli: Cli) -> None:
    cli.ok(
        "project",
        "create",
        "--name",
        "Rollback Tool",
        "--description",
        "d",
        "--objective",
        "o",
    )
    cli.ok("workflow", "transition", "--reason", "start")
    drafted = cli.ok("stage", "execute", "--stage", "research")
    # Proposal IDs still need the flag; the project is implied.
    approved = cli.ok("proposal", "approve", "--proposal-id", drafted.first_uuid())
    assert "committed" in approved.stdout

    status = cli.ok("workflow", "status", "--project-id", "rollback tool")
    assert "planning" in status.stdout


def test_current_project_survives_between_commands_and_can_be_switched(
    cli: Cli,
) -> None:
    for name in ("First", "Second"):
        cli.ok(
            "project",
            "create",
            "--name",
            name,
            "--description",
            "d",
            "--objective",
            "o",
        )

    assert "Current project: Second" in cli.ok("project", "list").stdout
    cli.ok("project", "use", "--project-id", "first")
    assert "Current project: First" in cli.ok("project", "list").stdout
    assert (cli.cwd / "workspace" / ".atlas-current-project").is_file()


def test_unknown_project_name_is_a_parse_error(cli: Cli) -> None:
    cli.ok(
        "project", "create", "--name", "Only", "--description", "d", "--objective", "o"
    )

    result = cli("workflow", "status", "--project-id", "missing")

    assert result.returncode == 2
    assert "No project matches 'missing'" in result.stdout
