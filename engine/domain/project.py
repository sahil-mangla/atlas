"""Project aggregate root for the ATLAS domain.

Project is the top-level entry point to all domain concepts. It holds
references to its owned sub-aggregates by ID rather than embedding them
directly, keeping the root lightweight and decoupled from the full state
of each sub-aggregate.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import ProjectStatus, WorkflowStage


class Project(BaseModel):
    """The root aggregate governing the complete engineering project lifecycle.

    Project is the single owner of all domain contexts (Workspace, Research,
    Roadmap, Architecture, Workflow, Memory, Evaluations). It references each
    by ID to remain lightweight and avoid circular coupling.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique project identifier.",
    )
    name: str = Field(
        description="Human-readable project name.",
    )
    description: str = Field(
        description="Short summary of the project goals.",
    )
    objective: str = Field(
        description="High-level engineering goal or vision statement.",
    )
    status: ProjectStatus = Field(
        default=ProjectStatus.INITIALIZED,
        description="Operational lifecycle state of the project.",
    )
    current_stage: WorkflowStage = Field(
        default=WorkflowStage.IDEA,
        description="Active phase in the engineering workflow.",
    )
    workspace_id: UUID | None = Field(
        default=None,
        description="Reference to the associated Workspace.",
    )
    roadmap_id: UUID | None = Field(
        default=None,
        description="Reference to the active Roadmap.",
    )
    architecture_id: UUID | None = Field(
        default=None,
        description="Reference to the Architecture design context.",
    )
    research_id: UUID | None = Field(
        default=None,
        description="Reference to the Research context.",
    )
    memory_id: UUID | None = Field(
        default=None,
        description="Reference to the persistent Memory context.",
    )
    workflow_id: UUID | None = Field(
        default=None,
        description="Reference to the active Workflow state machine.",
    )
    evaluation_ids: list[UUID] = Field(
        default_factory=list,
        description="References to all Evaluations conducted against this project.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the project was initialized.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of the most recent modification.",
    )
