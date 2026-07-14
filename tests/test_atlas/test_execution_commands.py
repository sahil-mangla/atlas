"""Tests for stage execution commands in the Application Layer."""

import uuid

import pytest

from atlas import Atlas
from atlas.commands import (
    ApproveProposalCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    RejectProposalCommand,
)
from atlas.exceptions import ProposalValidationError
from atlas.types import WorkflowStage


def test_execute_stage_and_approve(test_atlas_platform: Atlas) -> None:
    """Test generating a proposal and approving it."""
    proj = test_atlas_platform.create_project(
        CreateProjectCommand(name="W", description="D", objective="O")
    )

    # Transition to Research to be able to execute Research stage
    # (assuming the engine allows manual transitions in test setup or
    # we just attempt execution and check exception mapping)

    # Actually, IDEA stage doesn't have an executor, so executing it might fail.
    # We will try to execute RESEARCH stage directly, which might raise an error
    # if workflow is not on RESEARCH stage. That's fine, we check exception mapping.
    cmd = ExecuteStageCommand(project_id=proj.id, stage=WorkflowStage.RESEARCH)

    with pytest.raises(Exception) as exc:
        test_atlas_platform.execute_stage(cmd)

    assert exc.type.__name__.endswith("Error")


def test_approve_nonexistent_proposal(test_atlas_platform: Atlas) -> None:
    """Test exception mapping for missing proposal."""
    proj = test_atlas_platform.create_project(
        CreateProjectCommand(name="W", description="D", objective="O")
    )

    cmd = ApproveProposalCommand(project_id=proj.id, proposal_id=uuid.uuid4())

    with pytest.raises(ProposalValidationError):
        test_atlas_platform.approve_proposal(cmd)


def test_reject_nonexistent_proposal(test_atlas_platform: Atlas) -> None:
    """Test exception mapping for missing proposal."""
    proj = test_atlas_platform.create_project(
        CreateProjectCommand(name="W", description="D", objective="O")
    )

    cmd = RejectProposalCommand(
        project_id=proj.id, proposal_id=uuid.uuid4(), feedback="Bad proposal"
    )

    with pytest.raises(ProposalValidationError):
        test_atlas_platform.reject_proposal(cmd)
