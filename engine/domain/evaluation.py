"""Evaluation domain assessment models for the ATLAS platform.

Assessment records quality findings, requirement coverage matrices, and implementation
readiness decisions.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import (
    EvaluationStatus,
    FindingSeverity,
    FindingCategory,
    FindingLifecycleStatus,
)
from engine.domain.metadata import ArtifactMetadata, ArtifactStatus


class EvaluationFinding(BaseModel):
    """A single assessment audit observation produced during evaluation."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this finding.",
    )
    severity: FindingSeverity = Field(
        description="Severity of this finding (e.g. info, warning, blocking).",
    )
    category: FindingCategory = Field(
        description="Finding domain category (e.g. traceability, risk).",
    )
    description: str = Field(description="Summary of the review observation.")
    evidence: str = Field(description="Detailed engineering findings or observations.")
    recommendation: str = Field(description="Action suggested to resolve finding.")
    traceability_links: list[UUID] = Field(
        default_factory=list,
        description="Identifiers of relevant components, tasks, ADRs, or research.",
    )
    lifecycle_status: FindingLifecycleStatus = Field(
        default=FindingLifecycleStatus.ACTIVE,
        description="State of the finding (active, resolved, waived).",
    )


class RequirementCoverage(BaseModel):
    """Checklist tracking satisfy status of a specific engineering requirement."""

    requirement_id: UUID = Field(
        description="Unique identifier of the target constraint or deliverable.",
    )
    requirement_type: str = Field(
        description="Target type ('deliverable' or 'constraint').",
    )
    description: str = Field(description="Summary of the requirement.")
    status: str = Field(
        description="Coverage classification ('satisfied', 'partially_satisfied', 'unsatisfied').",
    )
    justification: str = Field(
        description="Reasoning explaining this status allocation.",
    )


class ReadinessDecision(BaseModel):
    """The formal outcome assessing whether a project is ready for implementation."""

    ready: bool = Field(
        description="True if the project is ready for implementation.",
    )
    justification: str = Field(
        description="Detailed justification for this decision.",
    )


class EvaluationSummary(BaseModel):
    """Synthesis of the evaluation outcomes."""

    synthesis: str = Field(description="Overall synthesis of the evaluation.")
    total_findings: int = Field(default=0, description="Total findings recorded.")
    blocking_findings: int = Field(
        default=0, description="Total blocking issues recorded."
    )
    satisfied_requirements: int = Field(
        default=0, description="Total satisfied requirements."
    )
    partially_satisfied_requirements: int = Field(
        default=0, description="Total partially satisfied requirements."
    )
    unsatisfied_requirements: int = Field(
        default=0, description="Total unsatisfied requirements."
    )


class EvaluationSnapshot(BaseModel):
    """Immutable snapshot of a finalized evaluation pass."""

    metadata: ArtifactMetadata = Field(
        default_factory=ArtifactMetadata,
        description="Standardized artifact metadata.",
    )
    research_snapshot_id: UUID = Field(
        description="Research snapshot baseline evaluated.",
    )
    planning_snapshot_id: UUID = Field(
        description="Planning snapshot baseline evaluated.",
    )
    architecture_snapshot_id: UUID = Field(
        description="Architecture snapshot baseline evaluated.",
    )
    findings: list[EvaluationFinding] = Field(
        description="Findings captured in this evaluation pass.",
    )
    coverage: list[RequirementCoverage] = Field(
        description="Requirement coverage checklist.",
    )
    readiness_decision: ReadinessDecision = Field(
        description="Ready decision for this pass.",
    )
    summary: EvaluationSummary = Field(description="Summary synthesis.")


class Evaluation(BaseModel):
    """The authoritative quality assessment aggregate root."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique evaluation identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    status: ArtifactStatus = Field(
        default=ArtifactStatus.DRAFT,
        description="Lifecycle state of this quality assessment.",
    )
    research_snapshot_id: UUID = Field(
        description="Research snapshot baseline evaluated.",
    )
    planning_snapshot_id: UUID = Field(
        description="Planning snapshot baseline evaluated.",
    )
    architecture_snapshot_id: UUID = Field(
        description="Architecture snapshot baseline evaluated.",
    )

    # Active draft assessment state
    findings: list[EvaluationFinding] = Field(
        default_factory=list,
        description="Active draft findings.",
    )
    coverage: list[RequirementCoverage] = Field(
        default_factory=list,
        description="Active requirement coverage checklist.",
    )
    readiness_decision: ReadinessDecision | None = Field(
        default=None,
        description="Active readiness decision.",
    )
    summary: EvaluationSummary | None = Field(
        default=None,
        description="Active summary synthesis.",
    )

    # Historical immutable approved snapshots
    snapshots: list[EvaluationSnapshot] = Field(
        default_factory=list,
        description="Frozen evaluation snapshots.",
    )
