"""Research domain models for the ATLAS platform.

Research encapsulates all collected technical information, findings, and
knowledge gaps gathered before architectural commitments are made.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import ResearchStatus


class ResearchTopic(BaseModel):
    """A specific area targeted for technical investigation."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique topic identifier.",
    )
    title: str = Field(
        description="Name of the research topic.",
    )
    description: str = Field(
        default="",
        description="Scope of investigation for this topic.",
    )


class ResearchFinding(BaseModel):
    """A synthesized technical fact, trade-off, or solution option
    discovered during research.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique finding identifier.",
    )
    title: str = Field(
        description="Short label for the finding.",
    )
    summary: str = Field(
        description="Synthesized conclusion or technical insight.",
    )
    source: str = Field(
        default="",
        description="Origin of the finding — citation, URL, or experiment reference.",
    )


class KnowledgeGap(BaseModel):
    """An area where design information remains incomplete or unverified."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique gap identifier.",
    )
    description: str = Field(
        description="What is unknown, ambiguous, or unresolved.",
    )
    impact: str = Field(
        default="",
        description=(
            "Potential consequence if this gap is not addressed before architecture."
        ),
    )


class Research(BaseModel):
    """Accumulated technical and domain-specific knowledge for the project.

    Research records what is known, what has been discovered from external
    sources, and what uncertainties remain before design decisions are locked.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique research context identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    problem_statement: str = Field(
        default="",
        description="Detailed description of the problem under investigation.",
    )
    status: ResearchStatus = Field(
        default=ResearchStatus.PLANNED,
        description="Current progress state of the research phase.",
    )
    topics: list[ResearchTopic] = Field(
        default_factory=list,
        description="Specific areas targeted for technical investigation.",
    )
    literature: list[str] = Field(
        default_factory=list,
        description="Collected papers, documentation fragments, and technical notes.",
    )
    findings: list[ResearchFinding] = Field(
        default_factory=list,
        description="Synthesized conclusions, trade-offs, and technical facts.",
    )
    references: list[str] = Field(
        default_factory=list,
        description="Citations, source URLs, and external publications.",
    )
    knowledge_gaps: list[KnowledgeGap] = Field(
        default_factory=list,
        description="Areas where technical understanding remains incomplete.",
    )
