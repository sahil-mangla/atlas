"""Architecture domain models for the ATLAS platform.

Architecture is the technical design record — it owns system boundaries, component
definitions, ADRs, constraints, drivers, and assumptions. No other domain entity
modifies architecture state directly.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import ArchitectureStatus
from engine.domain.metadata import ArtifactMetadata


class InterfaceContract(BaseModel):
    """A public interface contract exposed by a component."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this interface contract.",
    )
    name: str = Field(description="Name of the interface.")
    description: str = Field(
        default="", description="Description of the interface purpose."
    )
    protocol: str = Field(
        description="Communication protocol (e.g. gRPC, HTTP/REST, Python API)."
    )
    input_schema: str = Field(description="Schema description of the inputs.")
    output_schema: str = Field(description="Schema description of the outputs.")


class ArchitectureDriver(BaseModel):
    """An architectural driver connecting research findings/objectives to design."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this driver.",
    )
    name: str = Field(description="Name of the driver.")
    description: str = Field(description="Details on why this driver exists.")
    driver_type: str = Field(
        description="Classification of the driver (e.g. Quality Attribute, Constraint)."
    )
    source_finding_ids: list[UUID] = Field(
        default_factory=list,
        description="Research findings driving this requirement.",
    )
    source_objective_ids: list[UUID] = Field(
        default_factory=list,
        description="Planning/Problem objectives driving this requirement.",
    )
    target_quality_attribute_ids: list[UUID] = Field(
        default_factory=list,
        description="Target quality attributes addressed by this driver.",
    )
    target_adr_ids: list[UUID] = Field(
        default_factory=list,
        description="Architectural decisions addressing this driver.",
    )


class ArchitectureComponent(BaseModel):
    """A subsystem, module, or boundary layer within the technical design."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique component identifier.",
    )
    name: str = Field(
        description="Name of the subsystem or module.",
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="Explicit list of responsibilities owned by this component.",
    )
    public_interfaces: list[InterfaceContract] = Field(
        default_factory=list,
        description="Public interface contracts exposed by this component.",
    )
    owned_data: list[str] = Field(
        default_factory=list,
        description="Databases, schemas, or storage partitions owned by this component.",
    )
    internal_dependencies: list[UUID] = Field(
        default_factory=list,
        description="IDs of other internal components this component depends on.",
    )
    external_dependencies: list[str] = Field(
        default_factory=list,
        description="External systems, APIs, or libraries this component depends on.",
    )
    related_adrs: list[UUID] = Field(
        default_factory=list,
        description="IDs of Architectural Decisions governing this component.",
    )
    related_risks: list[UUID] = Field(
        default_factory=list,
        description="IDs of Risks associated with this component.",
    )


class ArchitecturalDecision(BaseModel):
    """An Architectural Decision Record (ADR) documenting a design choice.

    Records the context, decision, rationale, trade-offs, and traceability
    of a significant design choice made during the architecture phase.
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
    problem_statement: str = Field(
        description="Formal statement of the problem being solved.",
    )
    decision: str = Field(
        description="The chosen design option or direction.",
    )
    rationale: str = Field(
        description="Why this option was selected over alternatives.",
    )
    alternatives_considered: list[str] = Field(
        default_factory=list,
        description="List of alternative options evaluated.",
    )
    reasons_rejected: list[str] = Field(
        default_factory=list,
        description="Why the considered alternatives were rejected.",
    )
    trade_offs: list[str] = Field(
        default_factory=list,
        description="Trade-offs accepted as part of this decision.",
    )
    consequences: str = Field(
        default="",
        description="Known trade-offs, limitations, or follow-on actions.",
    )
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when this decision was recorded.",
    )

    # Traceability links
    related_constraints: list[UUID] = Field(
        default_factory=list,
        description="Constraints that influenced this decision.",
    )
    related_assumptions: list[UUID] = Field(
        default_factory=list,
        description="Assumptions accepted under this decision.",
    )
    supporting_evidence: list[UUID] = Field(
        default_factory=list,
        description="Research evidence supporting this decision.",
    )
    related_planning_tasks: list[UUID] = Field(
        default_factory=list,
        description="Planning tasks mapped to this decision.",
    )
    related_research_findings: list[UUID] = Field(
        default_factory=list,
        description="Research findings motivating this decision.",
    )
    traceability_links: list[str] = Field(
        default_factory=list,
        description="General traceability paths or links.",
    )


class Risk(BaseModel):
    """An identified technical or architectural risk."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this risk.",
    )
    description: str = Field(description="Detailed description of the risk.")
    severity: str = Field(
        description="Severity classification (e.g. low, medium, high, critical)."
    )
    likelihood: str = Field(
        description="Likelihood of occurrence (e.g. low, medium, high)."
    )
    impact: str = Field(description="System impact (e.g. low, medium, high).")
    mitigation: str = Field(description="Mitigation plan.")
    owner: str = Field(description="Responsible individual or team.")
    related_decision_id: UUID | None = Field(
        default=None,
        description="Referenced ADR ID that mitigates or introduces this risk.",
    )


class Constraint(BaseModel):
    """An architectural constraint limiting technical choices."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique constraint identifier.",
    )
    description: str = Field(description="Description of the constraint.")
    impact: str = Field(
        description="How this constraint impacts technical choices.",
    )
    related_research_constraint_id: UUID | None = Field(
        default=None,
        description="Reference to upstream research constraint if any.",
    )


class Assumption(BaseModel):
    """A technical premise accepted as true for progression."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique assumption identifier.",
    )
    description: str = Field(description="Detailed description of the assumption.")
    risk: str = Field(
        description="Risk statement if the assumption is proven false.",
    )
    related_research_assumption_id: UUID | None = Field(
        default=None,
        description="Reference to upstream research assumption if any.",
    )


class QualityAttribute(BaseModel):
    """An architectural quality attribute driver."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique quality attribute identifier.",
    )
    name: str = Field(
        description="Name of the attribute (e.g. Scalability, Reliability)."
    )
    description: str = Field(description="Target standards or SLA definition.")
    mitigation_strategy: str = Field(
        description="Engineering strategy to fulfill this driver."
    )
    related_adrs: list[UUID] = Field(
        default_factory=list,
        description="ADR IDs implementing this strategy.",
    )


class ArchitectureSummary(BaseModel):
    """Synthesis of the technical architecture definition."""

    synthesis: str = Field(description="Overall synthesis of the architecture.")
    total_components: int = Field(
        default=0, description="Total components defined."
    )
    total_adrs: int = Field(default=0, description="Total ADRs recorded.")
    total_risks: int = Field(default=0, description="Total risks registered.")


class ArchitectureSnapshot(BaseModel):
    """Immutable snapshot of an approved architecture phase."""

    metadata: ArtifactMetadata = Field(
        default_factory=ArtifactMetadata,
        description="Standardized artifact metadata.",
    )
    planning_snapshot_id: UUID = Field(
        description="Approved PlanningSnapshot used as baseline."
    )
    research_snapshot_id: UUID = Field(
        description="Approved ResearchSnapshot used as baseline."
    )
    components: list[ArchitectureComponent] = Field(
        description="Architecture components."
    )
    decisions: list[ArchitecturalDecision] = Field(description="Recorded ADRs.")
    risks: list[Risk] = Field(description="Registered risks.")
    constraints: list[Constraint] = Field(description="Constraints.")
    assumptions: list[Assumption] = Field(description="Assumptions.")
    quality_attributes: list[QualityAttribute] = Field(
        description="Quality attributes."
    )
    summary: ArchitectureSummary = Field(description="Architecture summary.")


class Architecture(BaseModel):
    """The authoritative technical design aggregate root."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique architecture context identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    status: ArchitectureStatus = Field(
        default=ArchitectureStatus.DRAFT,
        description="Lifecycle state of this technical design.",
    )

    # Active draft technical state
    design_summary: str = Field(
        default="",
        description="High-level description of the technical design.",
    )
    drivers: list[ArchitectureDriver] = Field(
        default_factory=list,
        description="Active architecture drivers.",
    )
    components: list[ArchitectureComponent] = Field(
        default_factory=list,
        description="Subsystem component models.",
    )
    decisions: list[ArchitecturalDecision] = Field(
        default_factory=list,
        description="Catalog of Architectural Decision Records.",
    )
    risks: list[Risk] = Field(
        default_factory=list,
        description="Active risk register.",
    )
    constraints: list[Constraint] = Field(
        default_factory=list,
        description="Active design constraints.",
    )
    assumptions: list[Assumption] = Field(
        default_factory=list,
        description="Active technical assumptions.",
    )
    quality_attributes: list[QualityAttribute] = Field(
        default_factory=list,
        description="Active quality attributes.",
    )
    summary: ArchitectureSummary | None = Field(
        default=None,
        description="Active architecture summary.",
    )

    # Historical immutable approved snapshots
    snapshots: list[ArchitectureSnapshot] = Field(
        default_factory=list,
        description="Immutable frozen snapshots.",
    )
