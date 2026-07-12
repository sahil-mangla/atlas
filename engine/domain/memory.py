"""Memory domain models for the ATLAS platform.

Memory is the persistent engineering intelligence of the project — it
captures decisions, historical context, and lessons learned across
development sessions to prevent context erosion.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EngineeringDecision(BaseModel):
    """A chronological record of a significant technical trade-off or approval."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique decision record identifier.",
    )
    title: str = Field(
        description="Short label identifying the decision.",
    )
    context: str = Field(
        description="Situation or problem that prompted this decision.",
    )
    rationale: str = Field(
        description="The reasoning behind the chosen direction.",
    )
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when this decision was recorded in memory.",
    )


class MemoryEntry(BaseModel):
    """A unit of historical context, conversation log, or system output."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique memory entry identifier.",
    )
    summary: str = Field(
        description="One-line description of what this entry captures.",
    )
    content: str = Field(
        description="Full body of the context, dialogue, or output being preserved.",
    )
    source: str = Field(
        default="",
        description=(
            "Origin of this entry — session ID, subsystem name, or user reference."
        ),
    )
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when this entry was persisted.",
    )


class Memory(BaseModel):
    """The cumulative historical context and decision log of the project.

    Memory acts as a cross-cutting model, accumulating records from all
    other domain contexts to prevent context loss across sessions. It does
    not direct logic or enforce workflows in any subsystem.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique memory context identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    engineering_decisions: list[EngineeringDecision] = Field(
        default_factory=list,
        description="Chronological records of technical trade-offs and approvals.",
    )
    knowledge_entries: list[MemoryEntry] = Field(
        default_factory=list,
        description=(
            "Historical context items — session logs, user inputs, and system outputs."
        ),
    )
    lessons_learned: list[str] = Field(
        default_factory=list,
        description="Retrospective findings and post-mortems from completed work.",
    )
