"""Workflow domain model for the ATLAS platform.

Workflow represents the state-driven lifecycle tracking the project's
progress through the nine sequential engineering stages defined in the
ATLAS Engineering Lifecycle.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import ApprovalStatus, EvaluationStatus, WorkflowStage


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
        default_factory=datetime.utcnow,
        description="When the transition occurred.",
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
        default_factory=datetime.utcnow,
        description="When this review was generated.",
    )


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
        description="Stages that have been successfully navigated and signed off.",
    )
    pending_stages: list[WorkflowStage] = Field(
        default_factory=list,
        description="Remaining stages in the workflow sequence.",
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

    def record_transition(self, entry: WorkflowHistoryEntry) -> None:
        """Record a valid workflow transition.

        Args:
            entry: The history entry to record.
        """
        self.history.append(entry)
        self.current_stage = entry.new_stage

        # Re-calculate completed and pending lists
        stages = list(WorkflowStage)
        try:
            current_idx = stages.index(entry.new_stage)
            self.completed_stages = stages[:current_idx]
            self.pending_stages = stages[current_idx + 1 :]
        except ValueError:
            pass
