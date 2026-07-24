"""Tests for the CLI command parser."""

import uuid

import pytest

from atlas.commands import (
    ApproveProposalCommand,
    ArchiveProjectCommand,
    CompleteObjectiveCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    GetWorkflowStatusCommand,
    ListKnowledgeCandidatesCommand,
    ListProjectsCommand,
    LoadProjectCommand,
    RejectProposalCommand,
    ReviewKnowledgeCandidateCommand,
    ShowKnowledgeCandidateCommand,
    TransitionStageCommand,
)
from atlas.types import KnowledgeCandidateStatus, ProposalDecision, WorkflowStage
from clients.cli.commands import (
    HelpCommand,
    PresentationExportCommand,
    PresentationViewCommand,
    VersionCommand,
)
from clients.cli.parser import CLIParseError, parse_argv


def test_parse_no_args() -> None:
    with pytest.raises(CLIParseError, match="No command given"):
        parse_argv([])


def test_parse_unknown_group() -> None:
    with pytest.raises(CLIParseError, match="Unknown command group 'foo'"):
        parse_argv(["foo"])


def test_parse_help() -> None:
    cmd = parse_argv(["help"])
    assert isinstance(cmd, HelpCommand)


def test_parse_version() -> None:
    cmd = parse_argv(["version"])
    assert isinstance(cmd, VersionCommand)


# -- Project group -------------------------------------------------------------


def test_parse_project_missing_sub() -> None:
    with pytest.raises(CLIParseError, match="Missing project sub-command"):
        parse_argv(["project"])


def test_parse_project_create() -> None:
    cmd = parse_argv(
        [
            "project",
            "create",
            "--name",
            "Test",
            "--description",
            "Desc",
            "--objective",
            "Obj",
        ]
    )
    assert isinstance(cmd, CreateProjectCommand)
    assert cmd.name == "Test"
    assert cmd.description == "Desc"
    assert cmd.objective == "Obj"
    assert cmd.path is None


def test_parse_project_create_missing_flags() -> None:
    with pytest.raises(
        CLIParseError, match="Missing required flags: --description, --objective"
    ):
        parse_argv(["project", "create", "--name", "Test"])


def test_parse_project_create_accepts_flag_equals_value_syntax() -> None:
    cmd = parse_argv(
        [
            "project",
            "create",
            "--name=Test",
            "--description=Desc",
            "--objective=Obj",
        ]
    )
    assert isinstance(cmd, CreateProjectCommand)
    assert cmd.name == "Test"
    assert cmd.description == "Desc"
    assert cmd.objective == "Obj"


def test_parse_project_create_flag_equals_value_preserves_embedded_equals() -> None:
    cmd = parse_argv(
        [
            "project",
            "create",
            "--name=Test",
            "--description=x=y",
            "--objective=Obj",
        ]
    )
    assert isinstance(cmd, CreateProjectCommand)
    assert cmd.description == "x=y"


def test_parse_project_create_missing_value_raises_clear_error() -> None:
    """A flag immediately followed by another flag (value omitted) must
    raise a clear 'requires a value' error, not silently swallow the next
    flag name as the value."""
    with pytest.raises(CLIParseError, match="'--name' requires a value"):
        parse_argv(["project", "create", "--name", "--description", "Desc"])


def test_parse_project_create_repeated_flag_raises_clear_error() -> None:
    with pytest.raises(CLIParseError, match="'--name' was specified more than once"):
        parse_argv(
            [
                "project",
                "create",
                "--name",
                "A",
                "--description",
                "D",
                "--objective",
                "O",
                "--name",
                "B",
            ]
        )


def test_parse_project_load() -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(["project", "load", "--project-id", pid])
    assert isinstance(cmd, LoadProjectCommand)
    assert str(cmd.project_id) == pid


def test_parse_project_load_invalid_uuid() -> None:
    with pytest.raises(CLIParseError, match="not a valid UUID"):
        parse_argv(["project", "load", "--project-id", "not-a-uuid"])


def test_parse_project_list() -> None:
    cmd = parse_argv(["project", "list"])
    assert isinstance(cmd, ListProjectsCommand)


def test_parse_project_archive() -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(["project", "archive", "--project-id", pid])
    assert isinstance(cmd, ArchiveProjectCommand)
    assert str(cmd.project_id) == pid


# -- Workflow group ------------------------------------------------------------


def test_parse_workflow_missing_sub() -> None:
    with pytest.raises(CLIParseError, match="Missing workflow sub-command"):
        parse_argv(["workflow"])


def test_parse_workflow_status() -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(["workflow", "status", "--project-id", pid])
    assert isinstance(cmd, GetWorkflowStatusCommand)
    assert str(cmd.project_id) == pid


def test_parse_workflow_transition() -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(
        ["workflow", "transition", "--project-id", pid, "--reason", "Test reason"]
    )
    assert isinstance(cmd, TransitionStageCommand)
    assert str(cmd.project_id) == pid
    assert cmd.reason == "Test reason"
    assert cmd.actor == "cli"


def test_parse_workflow_complete_objective() -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(
        [
            "workflow",
            "complete-objective",
            "--project-id",
            pid,
            "--objective",
            "Resolve blocking bugs",
        ]
    )
    assert isinstance(cmd, CompleteObjectiveCommand)
    assert str(cmd.project_id) == pid
    assert cmd.objective == "Resolve blocking bugs"
    assert cmd.actor == "cli"


def test_parse_workflow_unknown_sub() -> None:
    pid = str(uuid.uuid4())
    with pytest.raises(CLIParseError, match="Unknown workflow sub-command"):
        parse_argv(["workflow", "bogus", "--project-id", pid])


# -- Stage group ---------------------------------------------------------------


def test_parse_stage_missing_sub() -> None:
    with pytest.raises(CLIParseError, match="Missing stage sub-command"):
        parse_argv(["stage"])


def test_parse_stage_execute() -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(["stage", "execute", "--project-id", pid, "--stage", "research"])
    assert isinstance(cmd, ExecuteStageCommand)
    assert str(cmd.project_id) == pid
    assert cmd.stage == WorkflowStage.RESEARCH


def test_parse_stage_execute_invalid_stage() -> None:
    pid = str(uuid.uuid4())
    with pytest.raises(CLIParseError, match="Invalid stage"):
        parse_argv(["stage", "execute", "--project-id", pid, "--stage", "foo"])


# -- Proposal group ------------------------------------------------------------


def test_parse_proposal_missing_sub() -> None:
    with pytest.raises(CLIParseError, match="Missing proposal sub-command"):
        parse_argv(["proposal"])


def test_parse_proposal_approve() -> None:
    pid = str(uuid.uuid4())
    propid = str(uuid.uuid4())
    cmd = parse_argv(
        [
            "proposal",
            "approve",
            "--project-id",
            pid,
            "--proposal-id",
            propid,
            "--actor",
            "user",
        ]
    )
    assert isinstance(cmd, ApproveProposalCommand)
    assert str(cmd.project_id) == pid
    assert str(cmd.proposal_id) == propid
    assert cmd.actor == "user"


def test_parse_proposal_reject() -> None:
    pid = str(uuid.uuid4())
    propid = str(uuid.uuid4())
    cmd = parse_argv(
        [
            "proposal",
            "reject",
            "--project-id",
            pid,
            "--proposal-id",
            propid,
            "--feedback",
            "Too slow",
        ]
    )
    assert isinstance(cmd, RejectProposalCommand)
    assert str(cmd.project_id) == pid
    assert str(cmd.proposal_id) == propid
    assert cmd.feedback == "Too slow"
    assert cmd.actor == "cli"


# -- Knowledge group ------------------------------------------------------------


def test_parse_knowledge_missing_sub() -> None:
    with pytest.raises(CLIParseError, match="Missing knowledge sub-command"):
        parse_argv(["knowledge"])


def test_parse_knowledge_list() -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(["knowledge", "list", "--project-id", pid])
    assert isinstance(cmd, ListKnowledgeCandidatesCommand)
    assert str(cmd.project_id) == pid
    assert cmd.status is None


def test_parse_knowledge_list_with_status() -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(["knowledge", "list", "--project-id", pid, "--status", "approved"])
    assert isinstance(cmd, ListKnowledgeCandidatesCommand)
    assert cmd.status == KnowledgeCandidateStatus.APPROVED


def test_parse_knowledge_list_invalid_status() -> None:
    pid = str(uuid.uuid4())
    with pytest.raises(CLIParseError, match="Invalid status"):
        parse_argv(["knowledge", "list", "--project-id", pid, "--status", "bogus"])


def test_parse_knowledge_show() -> None:
    pid = str(uuid.uuid4())
    cid = str(uuid.uuid4())
    cmd = parse_argv(["knowledge", "show", "--project-id", pid, "--candidate-id", cid])
    assert isinstance(cmd, ShowKnowledgeCandidateCommand)
    assert str(cmd.project_id) == pid
    assert str(cmd.candidate_id) == cid


def test_parse_knowledge_approve() -> None:
    pid = str(uuid.uuid4())
    cid = str(uuid.uuid4())
    cmd = parse_argv(
        ["knowledge", "approve", "--project-id", pid, "--candidate-id", cid]
    )
    assert isinstance(cmd, ReviewKnowledgeCandidateCommand)
    assert cmd.decision == ProposalDecision.APPROVE
    assert cmd.actor.actor_id == "cli"
    assert cmd.feedback is None


def test_parse_knowledge_reject() -> None:
    pid = str(uuid.uuid4())
    cid = str(uuid.uuid4())
    cmd = parse_argv(
        [
            "knowledge",
            "reject",
            "--project-id",
            pid,
            "--candidate-id",
            cid,
            "--feedback",
            "Not generalizable.",
        ]
    )
    assert isinstance(cmd, ReviewKnowledgeCandidateCommand)
    assert cmd.decision == ProposalDecision.REJECT
    assert cmd.feedback == "Not generalizable."


def test_parse_knowledge_reject_requires_feedback() -> None:
    pid = str(uuid.uuid4())
    cid = str(uuid.uuid4())
    with pytest.raises(CLIParseError, match="Missing required flags"):
        parse_argv(["knowledge", "reject", "--project-id", pid, "--candidate-id", cid])


def test_parse_knowledge_unknown_sub() -> None:
    pid = str(uuid.uuid4())
    with pytest.raises(CLIParseError, match="Unknown knowledge sub-command"):
        parse_argv(["knowledge", "bogus", "--project-id", pid])


# -- Presentation group ---------------------------------------------------------


def test_parse_presentation_missing_sub() -> None:
    with pytest.raises(CLIParseError, match="Missing presentation sub-command"):
        parse_argv(["presentation"])


@pytest.mark.parametrize(
    "view", ["dashboard", "workflow", "research", "knowledge", "diagnostics"]
)
def test_parse_presentation_view_defaults_to_cli_format(view: str) -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(["presentation", view, "--project-id", pid])
    assert isinstance(cmd, PresentationViewCommand)
    assert str(cmd.project_id) == pid
    assert cmd.view == view
    assert cmd.format == "cli"


def test_parse_presentation_view_explicit_format() -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(
        ["presentation", "dashboard", "--project-id", pid, "--format", "json"]
    )
    assert isinstance(cmd, PresentationViewCommand)
    assert cmd.format == "json"


def test_parse_presentation_view_invalid_format() -> None:
    pid = str(uuid.uuid4())
    with pytest.raises(CLIParseError, match="Invalid format"):
        parse_argv(
            ["presentation", "dashboard", "--project-id", pid, "--format", "xml"]
        )


def test_parse_presentation_export() -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(
        [
            "presentation",
            "export",
            "--project-id",
            pid,
            "--view",
            "diagnostics",
            "--output",
            "out.json",
            "--format",
            "json",
        ]
    )
    assert isinstance(cmd, PresentationExportCommand)
    assert cmd.view == "diagnostics"
    assert cmd.output == "out.json"
    assert cmd.format == "json"


def test_parse_presentation_export_defaults_to_cli_format() -> None:
    pid = str(uuid.uuid4())
    cmd = parse_argv(
        [
            "presentation",
            "export",
            "--project-id",
            pid,
            "--view",
            "workflow",
            "--output",
            "out.txt",
        ]
    )
    assert isinstance(cmd, PresentationExportCommand)
    assert cmd.format == "cli"


def test_parse_presentation_export_invalid_view() -> None:
    pid = str(uuid.uuid4())
    with pytest.raises(CLIParseError, match="Invalid view"):
        parse_argv(
            [
                "presentation",
                "export",
                "--project-id",
                pid,
                "--view",
                "bogus",
                "--output",
                "out.json",
            ]
        )


def test_parse_presentation_unknown_sub() -> None:
    pid = str(uuid.uuid4())
    with pytest.raises(CLIParseError, match="Unknown presentation sub-command"):
        parse_argv(["presentation", "bogus", "--project-id", pid])


# -- Flag parsing logic --------------------------------------------------------


def test_parse_unexpected_token() -> None:
    with pytest.raises(CLIParseError, match="Unexpected token 'bad'"):
        parse_argv(["project", "create", "bad", "--name", "Test"])


def test_parse_unknown_flag() -> None:
    with pytest.raises(CLIParseError, match="Unknown flag '--foo'"):
        parse_argv(["project", "create", "--foo", "bar"])


def test_parse_flag_missing_value() -> None:
    with pytest.raises(CLIParseError, match="Flag '--name' requires a value"):
        parse_argv(["project", "create", "--name"])
