"""Tests for the CLI command parser."""

import uuid

import pytest

from atlas.commands import (
    ApproveProposalCommand,
    ArchiveProjectCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    GetWorkflowStatusCommand,
    ListProjectsCommand,
    LoadProjectCommand,
    RejectProposalCommand,
    TransitionStageCommand,
)
from atlas.types import WorkflowStage
from clients.cli.commands import HelpCommand, VersionCommand
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
    ):  # noqa: E501
        parse_argv(["project", "create", "--name", "Test"])


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
