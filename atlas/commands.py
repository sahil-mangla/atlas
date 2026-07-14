"""Command contracts for the ATLAS public SDK.

Commands are typed, immutable, serializable, transport-independent inputs
passed to the Atlas facade.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from atlas.types import WorkflowStage


class Command(BaseModel):
    """Base class for all application commands."""

    model_config = ConfigDict(frozen=True)


class CreateProjectCommand(Command):
    """Initialize a new local engineering project."""

    name: str
    description: str
    objective: str
    path: str | None = None


class LoadProjectCommand(Command):
    """Load an existing project by ID."""

    project_id: UUID


class ListProjectsCommand(Command):
    """List all known projects."""


class ArchiveProjectCommand(Command):
    """Archive a project."""

    project_id: UUID


class ExecuteStageCommand(Command):
    """Execute a workflow stage with AI generation."""

    project_id: UUID
    stage: WorkflowStage


class ApproveProposalCommand(Command):
    """Approve a generated AI proposal."""

    project_id: UUID
    proposal_id: UUID
    actor: str = "unknown"


class RejectProposalCommand(Command):
    """Reject a generated AI proposal with feedback."""

    project_id: UUID
    proposal_id: UUID
    feedback: str
    actor: str = "unknown"


class TransitionStageCommand(Command):
    """Transition workflow to the next stage."""

    project_id: UUID


class GetWorkflowStatusCommand(Command):
    """Get current workflow state for a project."""

    project_id: UUID
