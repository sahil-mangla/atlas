"""Command contracts for the ATLAS public SDK.

Commands are typed, immutable, serializable, transport-independent inputs
passed to the Atlas facade.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from atlas.types import (
    KnowledgeActorType,
    KnowledgeCandidateStatus,
    ProposalDecision,
    WorkflowStage,
)


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
    reason: str | None = None
    actor: str = "unknown"


class CompleteObjectiveCommand(Command):
    """Mark one active stage objective as satisfied by human action.

    The public progression path for human-driven stages (PROBLEM_DEFINITION,
    IMPLEMENTATION, ITERATION, COMPLETION) that have no AI StageExecutor:
    clearing their active objectives is what readiness evaluation requires
    before ``TransitionStageCommand`` will succeed.
    """

    project_id: UUID
    objective: str
    actor: str = "unknown"


class GetWorkflowStatusCommand(Command):
    """Get current workflow state for a project."""

    project_id: UUID


class KnowledgeActorInput(BaseModel):
    """SDK-boundary mirror of ``engine.domain.knowledge.KnowledgeActor``.

    Kept separate so callers (including CLI adapters, which may never
    import ``engine`` directly) can construct a review actor without
    reaching past the SDK boundary.
    """

    model_config = ConfigDict(frozen=True)

    actor_type: KnowledgeActorType
    actor_id: str
    display_name: str = ""


class ReviewKnowledgeCandidateCommand(Command):
    """Approve or reject a pending engineering-knowledge candidate.

    Approval publishes the candidate in the same step
    (``KnowledgeApprovalService.approve_and_publish``) -- there is no
    separate publish action in the engine.
    """

    project_id: UUID
    candidate_id: UUID
    decision: ProposalDecision
    actor: KnowledgeActorInput
    feedback: str | None = None


class ListKnowledgeCandidatesCommand(Command):
    """List engineering-knowledge candidates for a project.

    Args:
        status: Optional filter. Omitted lists candidates in every status.
        format: Output format -- "cli" (default, truncated IDs) or "json"
            (full candidate IDs, machine-readable).
    """

    project_id: UUID
    status: KnowledgeCandidateStatus | None = None
    format: str = "cli"


class ShowKnowledgeCandidateCommand(Command):
    """Show a single engineering-knowledge candidate's full detail."""

    project_id: UUID
    candidate_id: UUID
