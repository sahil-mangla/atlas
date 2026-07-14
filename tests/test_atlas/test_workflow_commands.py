"""Tests for workflow-related commands in the Application Layer."""

import uuid

import pytest

from atlas import Atlas
from atlas.commands import (
    CreateProjectCommand,
    GetWorkflowStatusCommand,
    TransitionStageCommand,
)
from atlas.exceptions import WorkflowNotReadyError
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
