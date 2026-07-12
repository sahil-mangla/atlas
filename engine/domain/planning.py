"""Planning domain models for the ATLAS platform.

Planning translates approved research findings into structured roadmaps,
milestones, epics, tasks, and subtasks. It represents the engineering decomposition.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import PlanningStatus, TaskStatus
from engine.domain.metadata import ArtifactMetadata


class EngineeringDeliverable(BaseModel):
    """An engineering deliverable that the project must produce."""

    id: UUID = Field(
        default_factory=uuid4, description="Unique deliverable identifier."
    )
    title: str = Field(description="Title of the deliverable.")
    description: str = Field(default="", description="Description of the deliverable.")


class ScopeDefinition(BaseModel):
    """The scope definition of a planning phase."""

    statement: str = Field(description="Scope statement for the project.")
    deliverables: list[EngineeringDeliverable] = Field(
        default_factory=list, description="Target deliverables for this scope."
    )


class AcceptanceCriteria(BaseModel):
    """Functional validation requirements for a task or subtask."""

    criteria: list[str] = Field(
        default_factory=list, description="List of verifiable functional requirements."
    )


class DefinitionOfDone(BaseModel):
    """Quality standards required for completion of a task or subtask."""

    standards: list[str] = Field(
        default_factory=list, description="Quality standards (e.g. tests, linting)."
    )


class PlanningSubtask(BaseModel):
    """A granular subtask under a main task."""

    id: UUID = Field(default_factory=uuid4, description="Unique subtask identifier.")
    title: str = Field(description="Short description of the subtask.")
    description: str = Field(default="", description="Detailed objective.")
    dependencies: list[UUID] = Field(
        default_factory=list, description="IDs of tasks or subtasks this depends on."
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, description="Current execution state."
    )
    acceptance_criteria: AcceptanceCriteria = Field(default_factory=AcceptanceCriteria)
    definition_of_done: DefinitionOfDone = Field(default_factory=DefinitionOfDone)


class PlanningTask(BaseModel):
    """A task representing an execution step under an Epic."""

    id: UUID = Field(default_factory=uuid4, description="Unique task identifier.")
    title: str = Field(description="Short description of the work item.")
    description: str = Field(
        default="", description="Detailed implementation objective."
    )
    dependencies: list[UUID] = Field(
        default_factory=list, description="IDs of tasks this task depends on."
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, description="Current execution state."
    )
    acceptance_criteria: AcceptanceCriteria = Field(default_factory=AcceptanceCriteria)
    definition_of_done: DefinitionOfDone = Field(default_factory=DefinitionOfDone)
    subtasks: list[PlanningSubtask] = Field(
        default_factory=list, description="Granular subtasks under this task."
    )


class PlanningEpic(BaseModel):
    """An epic grouping a set of related planning tasks."""

    id: UUID = Field(default_factory=uuid4, description="Unique epic identifier.")
    title: str = Field(description="Name of the epic.")
    description: str = Field(default="", description="Scope and goals of this epic.")
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, description="Current execution state."
    )
    tasks: list[PlanningTask] = Field(
        default_factory=list, description="Tasks within this epic."
    )


class PlanningMilestone(BaseModel):
    """A high-level checkpoint grouping epics."""

    id: UUID = Field(default_factory=uuid4, description="Unique milestone identifier.")
    title: str = Field(description="Name of the milestone.")
    description: str = Field(
        default="", description="Scope and goals of this milestone."
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, description="Current execution state."
    )
    epics: list[PlanningEpic] = Field(
        default_factory=list, description="Epics within this milestone."
    )


class PlanningSummary(BaseModel):
    """Synthesis of the planning effort."""

    synthesis: str = Field(description="Summary of the planning results.")
    total_milestones: int = Field(
        default=0, description="Total number of milestones planned."
    )
    total_tasks: int = Field(default=0, description="Total number of tasks planned.")


class PlanningSnapshot(BaseModel):
    """Immutable snapshot of a completed planning phase."""

    metadata: ArtifactMetadata = Field(
        default_factory=ArtifactMetadata, description="Standardized artifact metadata."
    )
    research_snapshot_id: UUID = Field(
        description="Reference to the approved ResearchSnapshot this plan is based on."
    )
    scope_definition: ScopeDefinition = Field(description="Approved scope definition.")
    milestones: list[PlanningMilestone] = Field(description="Structured milestones.")
    summary: PlanningSummary = Field(description="Overall synthesis of the plan.")


class Planning(BaseModel):
    """The planning aggregate root tracking active drafts and snapshots."""

    id: UUID = Field(
        default_factory=uuid4, description="Unique planning context identifier."
    )
    project_id: UUID = Field(description="Reference to the owning Project.")
    status: PlanningStatus = Field(
        default=PlanningStatus.DRAFT,
        description="Current progress state of the planning phase.",
    )

    # Active Draft State
    scope_definition: ScopeDefinition | None = Field(
        default=None, description="Active scope definition draft."
    )
    milestones: list[PlanningMilestone] = Field(
        default_factory=list, description="Active milestones draft."
    )
    summary: PlanningSummary | None = Field(
        default=None, description="Active planning summary draft."
    )

    # Immutable Snapshots
    snapshots: list[PlanningSnapshot] = Field(
        default_factory=list, description="Historical immutable approved snapshots."
    )
