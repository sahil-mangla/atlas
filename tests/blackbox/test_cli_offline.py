"""Black-box tests: the installed CLI, end to end, with no network and no keys."""

import json
import re
from collections.abc import Callable

import pytest

from tests.blackbox.conftest import Cli

AI_STAGES = ("research", "planning", "architecture", "review")
_STAGE_LINE = re.compile(r"^Stage\s*:\s*(\S+)", re.MULTILINE)
_OBJECTIVE_LINE = re.compile(r"^• (.+)$", re.MULTILINE)
_MAX_HUMAN_STAGES = 6


def _stage(cli: Cli, project_id: str) -> str:
    status = cli.ok("workflow", "status", "--project-id", project_id)
    match = _STAGE_LINE.search(status.stdout)
    assert match, status.output
    return match.group(1)


def _objectives(cli: Cli, project_id: str) -> list[str]:
    status = cli.ok("workflow", "status", "--project-id", project_id).stdout
    section = status.split("── Objectives", 1)[1].split("──", 1)[0]
    return _OBJECTIVE_LINE.findall(section)


def _approve_stage(cli: Cli, project_id: str, stage: str) -> None:
    proposal_id = cli.ok(
        "stage", "execute", "--project-id", project_id, "--stage", stage
    ).first_uuid()
    approved = cli.ok(
        "proposal", "approve", "--project-id", project_id, "--proposal-id", proposal_id
    )
    assert "committed" in approved.stdout


def _run_ai_stages(cli: Cli, project_id: str) -> None:
    cli.ok("workflow", "transition", "--project-id", project_id, "--reason", "start")
    for stage in AI_STAGES:
        assert _stage(cli, project_id) == stage
        _approve_stage(cli, project_id, stage)


def test_version_needs_no_configuration_and_prints_nothing_else(cli: Cli) -> None:
    result = cli.ok("version", env={"ATLAS_AI_PROTOCOL": "GEMINI"})

    assert result.stdout.strip().startswith("ATLAS")
    assert result.stderr == ""
    assert cli.network_attempts() == []


def test_full_pipeline_runs_offline_to_completion(
    cli: Cli, project: Callable[[], str]
) -> None:
    project_id = project()
    _run_ai_stages(cli, project_id)

    # Human-driven stages have no AI executor: clear each objective by hand.
    for _ in range(_MAX_HUMAN_STAGES):
        stage = _stage(cli, project_id)
        objectives = _objectives(cli, project_id)
        if stage == "completion" and not objectives:
            break
        for objective in objectives:
            cli.ok(
                "workflow",
                "complete-objective",
                "--project-id",
                project_id,
                "--objective",
                objective,
            )
        if stage == "completion":
            break
        cli.ok("workflow", "transition", "--project-id", project_id, "--reason", "next")

    assert _stage(cli, project_id) == "completion"
    assert _objectives(cli, project_id) == []
    assert cli.network_attempts() == []


def test_pipeline_leaves_a_reviewable_record_on_disk(
    cli: Cli, project: Callable[[], str]
) -> None:
    project_id = project()
    _run_ai_stages(cli, project_id)

    approved = sorted(cli.cwd.rglob("atlas-proposals/approved/*.md"))
    assert len(approved) == len(AI_STAGES)
    assert not list(cli.cwd.rglob("atlas-proposals/pending/*.md"))
    # The offline research evidence must be unmistakably a fixture.
    records = [path.read_text(encoding="utf-8") for path in approved]
    research_record = next(r for r in records if r.startswith("# Research Proposal"))
    assert "[Demo fixture]" in research_record


def test_knowledge_review_round_trip(cli: Cli, project: Callable[[], str]) -> None:
    project_id = project()
    _run_ai_stages(cli, project_id)
    pid = ("--project-id", project_id)

    listing = cli.ok("knowledge", "list", *pid).stdout
    assert "pending_review" in listing

    dashboard = json.loads(
        cli.ok("presentation", "knowledge", *pid, "--format", "json").stdout
    )
    assert dashboard


def test_presentation_views_render_in_every_format(
    cli: Cli, project: Callable[[], str]
) -> None:
    project_id = project()
    _run_ai_stages(cli, project_id)

    for view in ("dashboard", "workflow", "research", "knowledge", "diagnostics"):
        for fmt in ("cli", "markdown", "json"):
            rendered = cli.ok(
                "presentation", view, "--project-id", project_id, "--format", fmt
            ).stdout
            assert rendered.strip(), f"{view}/{fmt} rendered nothing"
            if fmt == "json":
                json.loads(rendered)


def test_rejected_proposal_can_be_regenerated(
    cli: Cli, project: Callable[[], str]
) -> None:
    project_id = project()
    pid = ("--project-id", project_id)
    cli.ok("workflow", "transition", *pid, "--reason", "start")
    first = cli.ok("stage", "execute", *pid, "--stage", "research").first_uuid()

    cli.ok("proposal", "reject", *pid, "--proposal-id", first, "--feedback", "redo")

    assert _stage(cli, project_id) == "research"
    _approve_stage(cli, project_id, "research")
    assert _stage(cli, project_id) == "planning"


@pytest.mark.parametrize(
    "fault", ["malformed-json", "schema-violation", "truncated", "provider-error"]
)
def test_provider_failure_is_reported_cleanly_and_is_recoverable(
    cli: Cli, project: Callable[[], str], fault: str
) -> None:
    project_id = project()
    pid = ("--project-id", project_id)
    cli.ok("workflow", "transition", *pid, "--reason", "start")

    failed = cli(
        "stage", "execute", *pid, "--stage", "research", env={"ATLAS_AI_MODEL": fault}
    )

    assert failed.returncode != 0
    assert "Traceback" not in failed.output
    assert "error" in failed.output.lower()
    # Nothing half-written: the same stage succeeds on the next attempt.
    assert _stage(cli, project_id) == "research"
    _approve_stage(cli, project_id, "research")


def test_default_protocol_without_a_key_explains_what_to_set(
    cli: Cli, project: Callable[[], str]
) -> None:
    """The first thing a new user hits: GEMINI is the default and needs a key."""
    project_id = project()
    pid = ("--project-id", project_id)
    cli.ok("workflow", "transition", *pid, "--reason", "start")
    # Planning does no paper retrieval, so nothing but the provider can fail.
    _approve_stage(cli, project_id, "research")

    failed = cli(
        "stage",
        "execute",
        *pid,
        "--stage",
        "planning",
        env={"ATLAS_AI_PROTOCOL": "GEMINI"},
    )

    assert failed.returncode != 0
    assert "Traceback" not in failed.output
    assert "ATLAS_GEMINI_API_KEY" in failed.output
    assert cli.network_attempts() == []


def test_unknown_project_id_is_a_clean_error(cli: Cli) -> None:
    failed = cli(
        "workflow", "status", "--project-id", "00000000-0000-0000-0000-000000000000"
    )

    assert failed.returncode != 0
    assert "Traceback" not in failed.output


def test_corrupted_project_file_is_a_clean_error(
    cli: Cli, project: Callable[[], str]
) -> None:
    project_id = project()
    for path in cli.cwd.rglob(".atlas/*.json"):
        path.write_text("{ this is not json", encoding="utf-8")

    failed = cli("workflow", "status", "--project-id", project_id)

    assert failed.returncode != 0
    assert "Traceback" not in failed.output


@pytest.mark.xfail(strict=True, reason="Plan 2: --help is not a recognised flag yet")
def test_help_flag_is_supported(cli: Cli) -> None:
    assert cli("--help").returncode == 0
