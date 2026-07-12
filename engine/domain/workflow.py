"""Workflow domain model for the ATLAS platform.

Workflow represents the state-driven lifecycle tracking the project's
progress through the nine sequential engineering stages defined in the
ATLAS Engineering Lifecycle.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import WorkflowStage


class Workflow(BaseModel):
    """The state machine governing movement through the engineering lifecycle.

    Workflow tracks which stage is active, which have been completed,
    and what objectives must be met before the next transition. It does
    not contain design logic — that belongs to Architecture and Research.
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
