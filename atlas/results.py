"""Result contracts for the ATLAS public SDK.

Results are typed, pure DTO outputs returned from the Atlas facade.
They never expose engine internals or repositories.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from atlas.types import EvaluationStatus, ProjectStatus, ProposalStatus, WorkflowStage


class Result(BaseModel):
    """Base class for all application results."""

    model_config = ConfigDict(frozen=True)


class OperationResult(Result):
    """Generic success/failure envelope for commands with no content return."""

    success: bool
    message: str | None = None


class ProjectResult(Result):
    """Summary of a project."""

    id: UUID
    name: str
    description: str
    objective: str
    status: ProjectStatus


class ProjectListResult(Result):
    """Paginated list of ProjectResult items."""

    projects: list[ProjectResult]


class WorkflowStatusResult(Result):
    """Current workflow state for a project."""

    project_id: UUID
    current_stage: WorkflowStage
    objectives: list[str]
    is_ready_for_transition: bool
    readiness_status: EvaluationStatus
    blocking_issues: list[str] = Field(default_factory=list)
    pending_knowledge_candidates: list[UUID] = Field(default_factory=list)


class ProposalResult(Result):
    """Draft content, metadata, and status of an AI proposal."""

    id: UUID
    project_id: UUID
    stage: WorkflowStage
    status: ProposalStatus
    content: dict[str, Any]
    created_at: datetime | None = None


class CommitResult(Result):
    """Outcome of a committed proposal."""

    success: bool
    proposal_id: UUID
    patch_summary: str
    transition_blocked: bool = False
    blocking_issues: tuple[str, ...] = ()


class KnowledgeCandidateResult(Result):
    """Summary of one engineering-knowledge candidate."""

    id: UUID
    project_id: UUID
    title: str
    content: str
    category: str
    tags: tuple[str, ...] = ()
    status: str
    rationale: str = ""
    review_comment: str | None = None
    created_at: datetime


class KnowledgeCandidateListResult(Result):
    """A project's engineering-knowledge candidates."""

    candidates: list[KnowledgeCandidateResult]
