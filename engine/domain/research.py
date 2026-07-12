"""Research domain models for the ATLAS platform.

Research encapsulates all collected technical information, evidence, findings,
and opportunities gathered before architectural commitments are made.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import ResearchStatus
from engine.domain.metadata import ArtifactMetadata


class ProblemDefinition(BaseModel):
    """The core problem statement and research objectives."""

    statement: str = Field(description="Detailed description of the problem.")
    objectives: list[str] = Field(
        default_factory=list,
        description="Key objectives the research must achieve.",
    )


class ResearchSource(BaseModel):
    """An external source of information (URL, paper, internal doc, etc.)."""

    id: UUID = Field(default_factory=uuid4, description="Unique source identifier.")
    title: str = Field(description="Name or title of the source.")
    url_or_reference: str = Field(description="URL, DOI, or internal reference.")
    accessed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the source was last accessed.",
    )


class Evidence(BaseModel):
    """A first-class domain object representing raw information gathered."""

    id: UUID = Field(default_factory=uuid4, description="Unique evidence identifier.")
    type: str = Field(description="Type of evidence (e.g., literature, experiment).")
    title: str = Field(description="Short title for the evidence.")
    origin: str = Field(description="Origin context of this evidence.")
    citation: str = Field(description="Formal citation or reference string.")
    summary: str = Field(description="Summary of the gathered information.")
    confidence: float = Field(default=1.0, description="Confidence in this evidence.")
    tags: list[str] = Field(default_factory=list, description="Categorization tags.")
    notes: str = Field(default="", description="Optional context or notes.")
    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the evidence was collected.",
    )


class ResearchFinding(BaseModel):
    """A synthesized technical fact or insight derived from Evidence."""

    id: UUID = Field(default_factory=uuid4, description="Unique finding identifier.")
    title: str = Field(description="Short label for the finding.")
    summary: str = Field(description="Synthesized conclusion or technical insight.")
    evidence_ids: list[UUID] = Field(
        min_length=1,
        description="Must reference one or more Evidence objects.",
    )


class Constraint(BaseModel):
    """Technical or business limitation discovered during research."""

    id: UUID = Field(default_factory=uuid4, description="Unique constraint identifier.")
    description: str = Field(description="Description of the constraint.")
    impact: str = Field(description="How this constraint impacts architecture.")
    finding_ids: list[UUID] = Field(
        default_factory=list,
        description="Findings that support this constraint.",
    )


class Assumption(BaseModel):
    """A hypothesis accepted as true for the sake of progression."""

    id: UUID = Field(default_factory=uuid4, description="Unique assumption identifier.")
    description: str = Field(description="Description of the assumption.")
    risk: str = Field(description="Potential risk if the assumption is false.")


class Opportunity(BaseModel):
    """Engineering value discovered from validated findings."""

    id: UUID = Field(
        default_factory=uuid4, description="Unique opportunity identifier."
    )
    title: str = Field(description="Short title of the opportunity.")
    description: str = Field(description="Description of the engineering value.")
    finding_ids: list[UUID] = Field(
        min_length=1,
        description="Must reference one or more Findings.",
    )


class ResearchSummary(BaseModel):
    """High-level synthesis of the overall research outcome."""

    synthesis: str = Field(description="Overall synthesis of the research.")
    key_takeaways: list[str] = Field(
        default_factory=list,
        description="Main points to remember.",
    )


class ResearchSnapshot(BaseModel):
    """Immutable snapshot of a completed research phase."""

    metadata: ArtifactMetadata = Field(
        default_factory=ArtifactMetadata, description="Standardized artifact metadata."
    )
    problem_definition: ProblemDefinition = Field(description="Problem state.")
    research_sources: list[ResearchSource] = Field(description="Sources used.")
    evidence: list[Evidence] = Field(description="Gathered evidence.")
    findings: list[ResearchFinding] = Field(description="Synthesized findings.")
    constraints: list[Constraint] = Field(description="Discovered constraints.")
    assumptions: list[Assumption] = Field(description="Accepted assumptions.")
    opportunities: list[Opportunity] = Field(description="Discovered opportunities.")
    open_questions: list[str] = Field(description="Remaining open questions.")
    summary: ResearchSummary = Field(description="Overall synthesis.")
    confidence: float = Field(description="Confidence in the research snapshot.")


class Research(BaseModel):
    """Accumulated technical and domain-specific knowledge for the project.

    Research manages both active draft state and immutable approved snapshots.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique research context identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    status: ResearchStatus = Field(
        default=ResearchStatus.DRAFT,
        description="Current progress state of the research phase.",
    )

    # Active Draft State
    problem_definition: ProblemDefinition | None = Field(
        default=None, description="Active problem definition draft."
    )
    sources: list[ResearchSource] = Field(
        default_factory=list, description="Active sources."
    )
    evidence: list[Evidence] = Field(
        default_factory=list, description="Active evidence."
    )
    findings: list[ResearchFinding] = Field(
        default_factory=list, description="Active findings."
    )
    constraints: list[Constraint] = Field(
        default_factory=list, description="Active constraints."
    )
    assumptions: list[Assumption] = Field(
        default_factory=list, description="Active assumptions."
    )
    opportunities: list[Opportunity] = Field(
        default_factory=list, description="Active opportunities."
    )
    open_questions: list[str] = Field(
        default_factory=list, description="Active open questions."
    )

    # Immutable Snapshots
    snapshots: list[ResearchSnapshot] = Field(
        default_factory=list,
        description="Historical immutable approved snapshots.",
    )
