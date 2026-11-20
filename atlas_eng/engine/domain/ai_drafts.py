"""Strongly typed AI generation draft models mirroring domain aggregates."""

import re
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from atlas_eng.engine.domain.enums import (
    FindingCategory,
    FindingSeverity,
    KnowledgeCategory,
    KnowledgeSourceType,
)

# ==========================================
# Research Draft Hierarchy
# ==========================================


class SummaryDraft(BaseModel):
    """Output of ``SummaryPromptTemplate`` -- a condensed engineering summary."""

    summary: str = Field(description="Condensed summary of the given context.")


class EvidenceSummaryBatchDraft(BaseModel):
    """Output of the evidence-summarization pass.

    Deliberately narrow: the LLM's only job when grounding research is
    condensing real abstracts into plain-language summaries, in the same
    order they were given. Title, citation, and origin are built
    deterministically from source metadata elsewhere and never touch this
    model, so there is nothing here for the LLM to fabricate.
    """

    summaries: list[str] = Field(
        description="One summary per input abstract, same order as given."
    )


class ResearchEvidenceDraft(BaseModel):
    title: str = Field(description="Title of the raw evidence.")
    type: str = Field(default="document", description="Type of evidence.")
    origin: str = Field(
        default="AI Suggestion", description="Where the evidence came from."
    )
    citation: str = Field(default="AI Generated", description="Source citation.")
    summary: str = Field(description="Summary of the evidence.")
    external_id: str = Field(
        default="",
        description=(
            "Source-specific identifier (arXiv ID, DOI, OpenAlex ID) of the "
            "retrieved paper this evidence is grounded in. Used to verify "
            "generated proposals reference real, retrieved evidence rather "
            "than fabricating or altering it."
        ),
    )


class ResearchFindingDraft(BaseModel):
    title: str = Field(description="Title of the synthesized finding.")
    summary: str = Field(description="Synthesized details of the finding.")
    evidence_indices: list[int] = Field(
        default_factory=list,
        description=(
            "0-based indices of evidence from the proposal's evidence "
            "list that support this finding. At least one is required: leave "
            "out any finding that none of the evidence supports."
        ),
    )


class ResearchConstraintDraft(BaseModel):
    description: str = Field(
        description="Technological or business constraint description."
    )
    impact: str = Field(description="Determined impact of the constraint.")
    finding_indices: list[int] = Field(
        default_factory=list,
        description=(
            "0-based indices of findings from the proposal's findings "
            "list that support this constraint."
        ),
    )


class ResearchAssumptionDraft(BaseModel):
    description: str = Field(description="Engineering assumption.")
    risk: str = Field(description="Risk associated with this assumption.")


class ResearchOpportunityDraft(BaseModel):
    title: str = Field(description="Proposed engineering opportunity.")
    description: str = Field(description="Description of the opportunity.")
    finding_indices: list[int] = Field(
        default_factory=list,
        description=(
            "0-based indices of findings from the proposal's findings "
            "list that support this opportunity. At least one is required: "
            "leave out any opportunity that none of the findings supports."
        ),
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


class PlanningDeliverableDraft(BaseModel):
    title: str = Field(description="Deliverable title.")
    description: str = Field(default="", description="Deliverable description.")


class PlanningSubtaskDraft(BaseModel):
    title: str = Field(description="Subtask title.")


class PlanningTaskDraft(BaseModel):
    title: str = Field(description="Main task title.")
    description: str = Field(description="Task description.")
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
    deliverables: list[PlanningDeliverableDraft] = Field(
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
    internal_dependencies: list[str] = Field(
        default_factory=list,
        description=(
            "Components in this proposal that this one calls or reads from. Each "
            "entry is the exact `name` of another component in `components`, with "
            "no notes added; list alternatives as separate entries. Dependencies "
            "must not form a cycle."
        ),
    )
    external_dependencies: list[str] = Field(
        default_factory=list,
        description=(
            "Systems outside this proposal (databases, cloud services, "
            "third-party APIs) that this component relies on."
        ),
    )


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

    @model_validator(mode="after")
    def _resolve_dependency_names(self) -> "ArchitectureProposalDraft":
        """Rewrite each internal dependency to the exact component name it means.

        Models often refer to a component loosely: "Server-side SDK" for
        "Server-side SDK (Go, Java)", "Store (via replica)", or "Gateway or
        Relay". A reference is rewritten only when it points at exactly one
        component; anything else is left as written for the validator to reject.
        """
        names = [component.name.strip() for component in self.components]
        for component in self.components:
            resolved: list[str] = []
            for reference in component.internal_dependencies:
                for name in resolve_component_reference(reference, names):
                    if name not in resolved:
                        resolved.append(name)
            component.internal_dependencies = resolved
        return self


_PARENTHETICAL = re.compile(r"\([^)]*\)")
_ALTERNATIVES = re.compile(r"\s+(?:or|and)\s+|\s*/\s*|\s*,\s*", re.IGNORECASE)
_HALVES = re.compile(r"\s*&\s*|\s+and\s+")


def _name_key(text: str) -> str:
    return " ".join(_PARENTHETICAL.sub(" ", text).casefold().split())


def _match_one(reference: str, names: list[str]) -> str | None:
    key = _name_key(reference)
    if not key:
        return None
    exact = [name for name in names if _name_key(name) == key]
    if len(exact) == 1:
        return exact[0]
    prefixed = [name for name in names if _name_key(name).startswith(key + " ")]
    if len(prefixed) == 1:
        return prefixed[0]
    # A merged component such as "Tracker & Telemetry Pipeline" answers to
    # either half.
    halves = [
        name
        for name in names
        if any(
            half == key or half.startswith(key + " ")
            for half in _HALVES.split(_name_key(name))
        )
    ]
    return halves[0] if len(halves) == 1 else None


def resolve_component_reference(reference: str, names: list[str]) -> list[str]:
    """Map a loosely written component reference to exact component names.

    Returns the reference unchanged (stripped) when it cannot be resolved
    unambiguously, so validation can report it.
    """
    stripped = reference.strip()
    if stripped in names:
        return [stripped]
    single = _match_one(stripped, names)
    if single is not None:
        return [single]
    parts = _ALTERNATIVES.split(_PARENTHETICAL.sub(" ", stripped))
    matches = [_match_one(part, names) for part in parts if part.strip()]
    if len(matches) > 1 and all(match is not None for match in matches):
        return [match for match in matches if match is not None]
    return [stripped]


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


# ==========================================
# Knowledge Draft Hierarchy
# ==========================================


class KnowledgeCandidateDraft(BaseModel):
    title: str = Field(description="Title of the knowledge candidate.")
    content: str = Field(description="Content of the engineering knowledge.")
    category: KnowledgeCategory = Field(description="Category of the knowledge.")
    tags: list[str] = Field(description="Tags for the knowledge.")
    rationale: str = Field(description="Why this knowledge is important.")
    source_snapshot_type: KnowledgeSourceType | None = Field(
        default=None,
        description="The type of the snapshot that sourced this knowledge.",
    )
    source_snapshot_id: UUID | None = Field(
        default=None,
        description="The UUID of the snapshot that sourced this knowledge.",
    )
