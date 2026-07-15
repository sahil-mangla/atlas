"""Strongly typed AI generation draft models mirroring domain aggregates."""

from uuid import UUID

from pydantic import BaseModel, Field

from engine.domain.enums import FindingCategory, FindingSeverity

# ==========================================
# Research Draft Hierarchy
# ==========================================


class ResearchEvidenceDraft(BaseModel):
    title: str = Field(description="Title of the raw evidence.")
    type: str = Field(default="document", description="Type of evidence.")
    origin: str = Field(
        default="AI Suggestion", description="Where the evidence came from."
    )
    citation: str = Field(default="AI Generated", description="Source citation.")
    summary: str = Field(description="Summary of the evidence.")


class ResearchFindingDraft(BaseModel):
    title: str = Field(description="Title of the synthesized finding.")
    summary: str = Field(description="Synthesized details of the finding.")
    evidence_indices: list[int] = Field(
        default_factory=list,
        description="0-based indices of evidence from the proposal's evidence list that support this finding.",
    )


class ResearchConstraintDraft(BaseModel):
    description: str = Field(
        description="Technological or business constraint description."
    )
    impact: str = Field(description="Determined impact of the constraint.")
    finding_indices: list[int] = Field(
        default_factory=list,
        description="0-based indices of findings from the proposal's findings list that support this constraint.",
    )


class ResearchAssumptionDraft(BaseModel):
    description: str = Field(description="Engineering assumption.")
    risk: str = Field(description="Risk associated with this assumption.")


class ResearchOpportunityDraft(BaseModel):
    title: str = Field(description="Proposed engineering opportunity.")
    description: str = Field(description="Description of the opportunity.")
    finding_indices: list[int] = Field(
        default_factory=list,
        description="0-based indices of findings from the proposal's findings list that support this opportunity.",
    )


class ResearchProposalDraft(BaseModel):
    """Mirror of Research aggregate components before freeze."""

    problem_statement: str = Field(description="Core engineering problem description.")
    objectives: list[str] = Field(description="List of project research objectives.")
    evidence: list[ResearchEvidenceDraft] = Field(default_factory=list)
    findings: list[ResearchFindingDraft] = Field(default_factory=list)
    constraints: list[ResearchConstraintDraft] = Field(default_factory=list)
    assumptions: list[ResearchAssumptionDraft] = Field(default_factory=list)
    opportunities: list[ResearchOpportunityDraft] = Field(default_factory=list)


# ==========================================
# Planning Draft Hierarchy
# ==========================================


class PlanningSubtaskDraft(BaseModel):
    title: str = Field(description="Subtask title.")


class PlanningTaskDraft(BaseModel):
    title: str = Field(description="Main task title.")
    description: str = Field(description="Task description.")
    estimated_hours: int | None = Field(default=None, description="Estimate in hours.")
    subtasks: list[PlanningSubtaskDraft] = Field(default_factory=list)


class PlanningEpicDraft(BaseModel):
    title: str = Field(description="Epic title.")
    description: str = Field(description="Description of this Epic.")
    tasks: list[PlanningTaskDraft] = Field(default_factory=list)


class PlanningMilestoneDraft(BaseModel):
    title: str = Field(description="Milestone title.")
    description: str = Field(description="Milestone objectives.")
    epics: list[PlanningEpicDraft] = Field(default_factory=list)


class PlanningProposalDraft(BaseModel):
    """Mirror of Planning aggregate components before freeze."""

    scope_statement: str = Field(description="Comprehensive project scope statement.")
    deliverables: list[dict[str, str]] = Field(
        description="Key milestones deliverables."
    )
    milestones: list[PlanningMilestoneDraft] = Field(default_factory=list)


# ==========================================
# Architecture Draft Hierarchy
# ==========================================


class ArchitectureDriverDraft(BaseModel):
    driver_type: str = Field(
        description="Type of driver (e.g. QUALITY_ATTRIBUTE, CONSTRAINT)."
    )
    description: str = Field(description="Description of the driver.")


class ArchitectureComponentDraft(BaseModel):
    name: str = Field(description="Name of the component.")
    description: str = Field(description="Role and description.")
    responsibilities: list[str] = Field(default_factory=list)
    public_interfaces: list[str] = Field(default_factory=list)
    owned_data: list[str] = Field(default_factory=list)
    internal_dependencies: list[str] = Field(default_factory=list)
    external_dependencies: list[str] = Field(default_factory=list)


class ArchitecturalDecisionDraft(BaseModel):
    title: str = Field(description="ADR Title.")
    status: str = Field(description="ADR Status (e.g. ACCEPTED).")
    context: str = Field(description="Background context.")
    decision: str = Field(description="The architectural decision.")
    consequences: str = Field(description="The consequences of this decision.")


class ArchitectureRiskDraft(BaseModel):
    title: str = Field(description="Risk title.")
    description: str = Field(description="Description of potential failure mode.")
    severity: str = Field(description="Severity classification.")


class ArchitectureProposalDraft(BaseModel):
    """Mirror of Architecture aggregate components before freeze."""

    design_summary: str = Field(description="Overall technical design summary.")
    drivers: list[ArchitectureDriverDraft] = Field(default_factory=list)
    components: list[ArchitectureComponentDraft] = Field(default_factory=list)
    decisions: list[ArchitecturalDecisionDraft] = Field(default_factory=list)
    risks: list[ArchitectureRiskDraft] = Field(default_factory=list)


# ==========================================
# Evaluation Draft Hierarchy
# ==========================================


class EvaluationFindingDraft(BaseModel):
    title: str = Field(description="Finding title.")
    summary: str = Field(description="Detailed finding summary.")
    severity: FindingSeverity = Field(description="Severity (e.g. BLOCKING, ADVISORY).")
    category: FindingCategory = Field(
        description="Category (e.g. COMPLIANCE, QUALITY)."
    )


class EvaluationProposalDraft(BaseModel):
    """Mirror of Evaluation aggregate components before freeze."""

    synthesis: str = Field(description="Overall synthesis of quality evaluation.")
    findings: list[EvaluationFindingDraft] = Field(default_factory=list)


# ==========================================
# Commit Results
# ==========================================


class CommitResult(BaseModel):
    """Model returning the outcome of a proposal commit."""

    success: bool = Field(description="True if the proposal commit succeeded.")
    errors: list[str] = Field(
        default_factory=list, description="Commit validation or rollback errors."
    )
    committed_snapshot_id: UUID | None = Field(
        default=None, description="Frozen snapshot ID if generated."
    )
    transition_blocked: bool = Field(default=False)
    transition_errors: list[str] = Field(default_factory=list)
