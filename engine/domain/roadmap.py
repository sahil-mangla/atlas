"""Roadmap domain models for the ATLAS platform.

Roadmap is the single source of truth for scheduling, task prioritization,
milestone tracking, and overall implementation progress.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import Priority, TaskStatus


class Task(BaseModel):
    """A granular implementation item required to complete a milestone."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique task identifier.",
    )
    title: str = Field(
        description="Short description of the work item.",
    )
    description: str = Field(
        default="",
        description="Detailed implementation objective for this task.",
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current execution state of the task.",
    )
    priority: Priority = Field(
        default=Priority.MEDIUM,
        description="Execution urgency and ordering for this task.",
    )
    dependencies: list[UUID] = Field(
        default_factory=list,
        description="IDs of tasks that must complete before this one begins.",
    )
    specification_id: UUID | None = Field(
        default=None,
        description="Reference to the EngineeringSpecification that drives this task.",
    )


class Milestone(BaseModel):
    """A high-level release checkpoint grouping a set of related tasks."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique milestone identifier.",
    )
    title: str = Field(
        description="Name of the milestone.",
    )
    description: str = Field(
        default="",
        description="Scope and goals of this milestone.",
    )
    tasks: list[Task] = Field(
        default_factory=list,
        description="Granular implementation tasks required to reach this milestone.",
    )


class Roadmap(BaseModel):
    """The structured execution plan decomposing design goals into milestones and tasks.

    Roadmap is the sole owner of project scheduling, task states, and
    completion tracking. Progress must not be managed outside this boundary.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique roadmap identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    milestones: list[Milestone] = Field(
        default_factory=list,
        description="Ordered sequence of target release checkpoints.",
    )
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Aggregated completion percentage across all milestones.",
    )
