"""Architecture domain models for the ATLAS platform.

Architecture is the authoritative technical design record — it owns
system boundaries, component definitions, ADRs, constraints, and
assumptions. No other domain entity modifies architecture state directly.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ArchitecturalComponent(BaseModel):
    """A subsystem, module, or boundary layer within the technical design."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique component identifier.",
    )
    name: str = Field(
        description="Name of the subsystem or module.",
    )
    responsibility: str = Field(
        description="What this component owns and is responsible for.",
    )
    interfaces: list[str] = Field(
        default_factory=list,
        description="Named interfaces this component exposes to collaborators.",
    )
    collaborators: list[str] = Field(
        default_factory=list,
        description="Names of other components this component depends on.",
    )


class ArchitecturalDecision(BaseModel):
    """An Architectural Decision Record (ADR) documenting a design choice.

    Records the context, decision, rationale, and consequences of a
    significant technical choice made during the architecture phase.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique ADR identifier.",
    )
    title: str = Field(
        description="Short label for the architectural decision.",
    )
    context: str = Field(
        description="The problem or situation that required a decision.",
    )
    decision: str = Field(
        description="The chosen design option or direction.",
    )
    rationale: str = Field(
        description="Why this option was selected over alternatives.",
    )
    consequences: str = Field(
        default="",
        description="Known trade-offs, limitations, or follow-on actions.",
    )
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when this decision was recorded.",
    )


class Architecture(BaseModel):
    """The authoritative technical design record of the project.

    Architecture owns macro-level design, subsystem boundaries, ADRs,
    constraints, and assumptions. It acts as the baseline against which
    implementations are evaluated.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique architecture context identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    design_summary: str = Field(
        default="",
        description=(
            "Overall architectural pattern, paradigm, and high-level description."
        ),
    )
    components: list[ArchitecturalComponent] = Field(
        default_factory=list,
        description="Definitions of subsystems, modules, and boundary layers.",
    )
    decisions: list[ArchitecturalDecision] = Field(
        default_factory=list,
        description="Catalog of ADRs explaining design choices and trade-offs.",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="System limitations, style guidelines, and mandatory protocols.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Technical premises accepted during the design process.",
    )
