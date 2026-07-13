"""Workflow domain model for the ATLAS platform.

Workflow represents the state-driven lifecycle tracking the project's
progress through the nine sequential engineering stages defined in the
ATLAS Engineering Lifecycle.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import ApprovalStatus, EvaluationStatus, ProposalDecision, WorkflowStage


class WorkflowHistoryEntry(BaseModel):
    """Immutable record of a workflow stage transition."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique history entry identifier.",
    )
    previous_stage: WorkflowStage | None = Field(
        description="The stage before the transition, or None if initializing."
    )
    new_stage: WorkflowStage = Field(
        description="The stage transitioned to."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the transition occurred (timezone-aware UTC).",
    )
    approval_status: ApprovalStatus = Field(
        description="The human approval status of this transition."
    )
    reason: str = Field(
        description="The explanation or justification for this transition."
    )
    confidence: float = Field(
        default=1.0,
        description="Confidence score for this transition readiness.",
    )


class ReadinessReview(BaseModel):
    """Canonical review representing the readiness state of a workflow stage."""

    stage: WorkflowStage = Field(description="The stage evaluated.")
    status: EvaluationStatus = Field(description="The readiness outcome.")
    completed_objectives: list[str] = Field(
        default_factory=list, description="Objectives met for the stage."
    )
    blocking_issues: list[str] = Field(
        default_factory=list, description="Blocking errors preventing progression."
    )
    optional_improvements: list[str] = Field(
        default_factory=list, description="Suggested improvements."
    )
    confidence: float = Field(default=1.0, description="Readiness confidence score.")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this review was generated (timezone-aware UTC).",
    )


class ProposalReviewEntry(BaseModel):
    """Durable human decision recorded against an AI proposal."""

    proposal_id: UUID
    approver: str
    decision: ProposalDecision
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    comment: str | None = None


class Workflow(BaseModel):
    """The state machine governing movement through the engineering lifecycle.

    Workflow tracks which stage is active, which have been completed,
    and what objectives must be met before the next transition.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique workflow identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    current_stage: WorkflowStage = Field(
        default=WorkflowStage.IDEA,
        description="The active stage in the engineering lifecycle.",
    )
    completed_stages: list[WorkflowStage] = Field(
        default_factory=list,
        description=(
            "Stages from which a forward-approved transition was made. "
            "Append-only: backward transitions do not remove entries."
        ),
    )
    pending_stages: list[WorkflowStage] = Field(
        default_factory=list,
        description="Remaining stages not yet completed and not currently active.",
    )
    active_objectives: list[str] = Field(
        default_factory=list,
        description=(
            "Prerequisite checks and tasks required to transition to the next stage."
        ),
    )
    history: list[WorkflowHistoryEntry] = Field(
        default_factory=list,
        description="Immutable transition history.",
    )
    proposal_reviews: list[ProposalReviewEntry] = Field(default_factory=list)

    def record_proposal_review(self, entry: ProposalReviewEntry) -> None:
        """Persist an append-only human review decision."""
        self.proposal_reviews.append(entry)

    def record_transition(self, entry: WorkflowHistoryEntry) -> None:
        """Record a valid workflow transition.

        completed_stages is maintained as an append-only log of stages from
        which an explicit forward-approved transition was made. Backward
        transitions are preserved in history but do not remove stages from
        completed_stages and do not add the vacated stage as completed.

        Args:
            entry: The history entry to record.
        """
        self.history.append(entry)
        self.current_stage = entry.new_stage

        # Only mark the previous stage as completed on a genuine forward move.
        stages = list(WorkflowStage)
        if entry.previous_stage is not None:
            try:
                prev_idx = stages.index(entry.previous_stage)
                new_idx = stages.index(entry.new_stage)
                is_forward = new_idx > prev_idx
                if is_forward and entry.previous_stage not in self.completed_stages:
                    self.completed_stages.append(entry.previous_stage)
            except ValueError:
                pass

        # Pending: stages not yet completed and not the current active stage.
        self.pending_stages = [
            s for s in stages
            if s not in self.completed_stages and s != self.current_stage
        ]
