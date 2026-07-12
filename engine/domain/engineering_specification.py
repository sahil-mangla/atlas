"""EngineeringSpecification domain model for the ATLAS platform.

EngineeringSpecification models the formal, unambiguous implementation
instructions generated to guide developers or AI coding agents. It links
architectural design to executable tasks with clear acceptance criteria.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EngineeringSpecification(BaseModel):
    """Formal implementation instructions and constraints for a specific task.

    EngineeringSpecification is generated from Roadmap tasks and Architecture
    design rules. It is consumed by Evaluation to verify that code output
    meets all stated criteria and constraints.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique specification identifier.",
    )
    task_id: UUID | None = Field(
        default=None,
        description="Reference to the Roadmap Task this specification drives.",
    )
    title: str = Field(
        description="Short, human-readable name for this specification.",
    )
    objective: str = Field(
        description="The functional goal of the specific implementation task.",
    )
    scope: str = Field(
        default="",
        description=(
            "Boundaries of what is being modified — "
            "target components, files, or modules."
        ),
    )
    references: list[str] = Field(
        default_factory=list,
        description=(
            "Relevant blueprint sections, domain models, and codebase locations."
        ),
    )
    constraints: list[str] = Field(
        default_factory=list,
        description=(
            "Coding standards, performance parameters, and architectural boundaries."
        ),
    )
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description=("Verifiable statements determining whether the task is complete."),
    )
