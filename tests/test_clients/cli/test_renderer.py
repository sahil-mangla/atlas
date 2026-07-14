"""Tests for the CLI renderer."""

import uuid

from atlas.exceptions import InvalidProjectError
from atlas.results import (
    CommitResult,
    OperationResult,
    ProjectListResult,
    ProjectResult,
    ProposalResult,
    WorkflowStatusResult,
)
from atlas.types import EvaluationStatus, ProjectStatus, ProposalStatus, WorkflowStage
from clients.cli.renderer import CLIRenderer
from clients.common.progress import ProgressTracker
from clients.common.rendering import RenderContext


def test_render_project() -> None:
    renderer = CLIRenderer(RenderContext(terminal_width=40))
    res = ProjectResult(
        id=uuid.uuid4(),
        name="Test Proj",
        description="Desc",
        objective="Obj",
        status=ProjectStatus.INITIALIZED,
    )
    out = renderer.render_project(res)
    assert "Test Proj" in out
    assert "initialized" in out
    assert "Desc" in out


def test_render_project_list() -> None:
    renderer = CLIRenderer()
    res = ProjectListResult(projects=[
        ProjectResult(
            id=uuid.uuid4(),
            name="P1",
            description="D1",
            objective="O1",
            status=ProjectStatus.ACTIVE,
        )
    ])
    out = renderer.render_project_list(res)
    assert "Projects" in out
    assert "P1" in out
    assert "active" in out

    empty_res = ProjectListResult(projects=[])
    out_empty = renderer.render_project_list(empty_res)
    assert out_empty == "No projects found."


def test_render_workflow_status() -> None:
    renderer = CLIRenderer()
    res = WorkflowStatusResult(
        project_id=uuid.uuid4(),
        current_stage=WorkflowStage.RESEARCH,
        objectives=["Obj 1", "Obj 2"],
        is_ready_for_transition=False,
        readiness_status=EvaluationStatus.PENDING,
        blocking_issues=["Missing info"],
    )
    out = renderer.render_workflow_status(res)
    assert "Workflow Status" in out
    assert "research" in out
    assert "not ready" in out
    assert "Obj 1" in out
    assert "Missing info" in out


def test_render_proposal() -> None:
    renderer = CLIRenderer()
    res = ProposalResult(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        stage=WorkflowStage.RESEARCH,
        status=ProposalStatus.DRAFT,
        content={"data": "test content"},
    )
    out = renderer.render_proposal(res)
    assert "Proposal" in out
    assert "draft" in out
    assert "test content" in out


def test_render_operation() -> None:
    renderer = CLIRenderer()
    res = OperationResult(success=True, message="Done.")
    out = renderer.render_operation(res)
    assert "[✓ ok]" in out
    assert "Done." in out

    res_err = OperationResult(success=False, message="Failed.")
    out_err = renderer.render_operation(res_err)
    assert "[✗ failed]" in out_err
    assert "Failed." in out_err


def test_render_commit() -> None:
    renderer = CLIRenderer()
    res = CommitResult(success=True, proposal_id=uuid.uuid4(), patch_summary="Applied.")
    out = renderer.render_commit(res)
    assert "[✓ committed]" in out
    assert "Applied." in out


def test_render_error() -> None:
    renderer = CLIRenderer()
    err = InvalidProjectError("Bad project")
    out = renderer.render_error(err)
    assert "[✗ error]" in out
    assert "InvalidProjectError" in out
    assert "Bad project" in out


def test_render_parse_error() -> None:
    renderer = CLIRenderer()
    out = renderer.render_parse_error("Bad flags")
    assert "[✗ parse error]" in out
    assert "Bad flags" in out


def test_render_progress_tracker() -> None:
    renderer = CLIRenderer()
    tracker = ProgressTracker()
    tracker.start("Step 1")
    tracker.complete("Step 1")
    tracker.start("Step 2")
    out = renderer.render_progress_tracker(tracker)
    assert "✓  Step 1" in out
    assert "→  Step 2" in out


def test_render_version() -> None:
    renderer = CLIRenderer()
    out = renderer.render_version("1.0.0")
    assert out == "ATLAS  1.0.0"


def test_render_help() -> None:
    renderer = CLIRenderer()
    out = renderer.render_help()
    assert "Usage:" in out
    assert "atlas <group> <sub-command>" in out


def test_capability_aware_rendering() -> None:
    # Test with unicode enabled (default)
    renderer_unicode = CLIRenderer(RenderContext(use_unicode=True))
    res = OperationResult(success=True, message="Done.")
    out_unicode = renderer_unicode.render_operation(res)
    assert "✓" in out_unicode

    # Test with unicode disabled
    renderer_ascii = CLIRenderer(RenderContext(use_unicode=False))
    out_ascii = renderer_ascii.render_operation(res)
    assert "✓" not in out_ascii
    assert "v" in out_ascii

    # Test progress tracker ascii
    tracker = ProgressTracker()
    tracker.start("Step 1")
    tracker.complete("Step 1")
    out_tracker_ascii = renderer_ascii.render_progress_tracker(tracker)
    assert "✓" not in out_tracker_ascii
    assert "v  Step 1" in out_tracker_ascii
