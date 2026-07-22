"""Tests for workflow-related commands in the Application Layer."""

import uuid

import pytest

from atlas import Atlas
from atlas.commands import (
    CompleteObjectiveCommand,
    CreateProjectCommand,
    GetWorkflowStatusCommand,
    TransitionStageCommand,
)
from atlas.exceptions import ApplicationError, WorkflowNotReadyError
from atlas.types import WorkflowStage


def test_get_workflow_status(test_atlas_platform: Atlas) -> None:
    """Test retrieving workflow status."""
    proj = test_atlas_platform.create_project(
        CreateProjectCommand(name="W", description="D", objective="O")
    )

    cmd = GetWorkflowStatusCommand(project_id=proj.id)
    status_res = test_atlas_platform.get_workflow_status(cmd)

    assert status_res.project_id == proj.id
    assert status_res.current_stage == WorkflowStage.IDEA


def test_workflow_status_nonexistent_project(test_atlas_platform: Atlas) -> None:
    """Test exception mapping for nonexistent workflow."""
    cmd = GetWorkflowStatusCommand(project_id=uuid.uuid4())

    with pytest.raises(WorkflowNotReadyError):
        test_atlas_platform.get_workflow_status(cmd)


def test_transition_stage_without_readiness(test_atlas_platform: Atlas) -> None:
    """Test exception mapping when transitioning fails state machine rules."""
    proj = test_atlas_platform.create_project(
        CreateProjectCommand(name="W", description="D", objective="O")
    )

    cmd = TransitionStageCommand(project_id=proj.id)

    result = test_atlas_platform.transition_stage(cmd)
    assert result.current_stage == WorkflowStage.RESEARCH
    assert result.is_ready_for_transition is False


def test_complete_objective_clears_it_and_unblocks_readiness(
    test_atlas_platform: Atlas,
) -> None:
    """RC-001: completing every active objective for a stage must make
    readiness pass, mirroring the only public path off a human-driven
    stage that has no AI StageExecutor to clear objectives via commit."""
    proj = test_atlas_platform.create_project(
        CreateProjectCommand(name="W", description="D", objective="O")
    )
    test_atlas_platform.transition_stage(TransitionStageCommand(project_id=proj.id))

    status = test_atlas_platform.get_workflow_status(
        GetWorkflowStatusCommand(project_id=proj.id)
    )
    assert status.current_stage == WorkflowStage.RESEARCH
    assert status.objectives

    for objective in list(status.objectives):
        status = test_atlas_platform.complete_objective(
            CompleteObjectiveCommand(project_id=proj.id, objective=objective)
        )

    assert status.objectives == []
    assert status.is_ready_for_transition is True


def test_complete_objective_unknown_objective_raises(
    test_atlas_platform: Atlas,
) -> None:
    """Completing a string that isn't currently active must fail loudly
    rather than silently no-op, so a typo doesn't look like progress."""
    proj = test_atlas_platform.create_project(
        CreateProjectCommand(name="W", description="D", objective="O")
    )
    test_atlas_platform.transition_stage(TransitionStageCommand(project_id=proj.id))

    with pytest.raises(ApplicationError):
        test_atlas_platform.complete_objective(
            CompleteObjectiveCommand(project_id=proj.id, objective="not real")
        )
