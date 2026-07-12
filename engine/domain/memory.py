"""Memory domain models for the ATLAS platform.

Memory is the persistent engineering intelligence of the project — it
captures decisions, historical context, and artifacts across
development sessions using a hybrid append-only versioning model.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import MemoryCategory


class MemoryEntry(BaseModel):
    """A versioned unit of historical context, decisions, artifacts, or knowledge."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique memory entry identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    category: MemoryCategory = Field(
        description="The stable category of this memory.",
    )
    type: str = Field(
        description="Specific type of this entry (e.g., 'Architecture Decision').",
    )
    title: str = Field(
        description="Short label identifying the entry.",
    )
    content: str = Field(
        description="Full body of the knowledge, decision, or context being preserved.",
    )
    origin: str = Field(
        default="",
        description="Origin of this entry (e.g., subsystem name or user reference).",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Searchable keyword tags for this entry.",
    )
    confidence: float = Field(
        default=1.0,
        description="Confidence level of this knowledge (0.0 to 1.0).",
    )
    version: int = Field(
        default=1,
        description="Version number in the append-only history.",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this is the current active version.",
    )
    supersedes_id: UUID | None = Field(
        default=None,
        description="ID of the previous entry this one replaces.",
    )
    superseded_by_id: UUID | None = Field(
        default=None,
        description="ID of the new entry that replaces this one.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when this entry was persisted.",
    )


class Memory(BaseModel):
    """The cumulative historical context and decision log of the project.

    Memory acts as a cross-cutting model, accumulating versioned records
    from all other domain contexts to prevent context loss across sessions.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique memory context identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    entries: list[MemoryEntry] = Field(
        default_factory=list,
        description="All memory entries in the append-only log.",
    )

    def add_entry(self, entry: MemoryEntry) -> None:
        """Add a new memory entry."""
        self.entries.append(entry)

    def get_active_entries(self) -> list[MemoryEntry]:
        """Retrieve all currently active memory entries."""
        return [e for e in self.entries if e.is_active]

    def version_entry(self, old_entry_id: UUID, new_entry: MemoryEntry) -> None:
        """Version an entry by marking the old as superseded and linking the new.
        
        Args:
            old_entry_id: The UUID of the entry being superseded.
            new_entry: The new MemoryEntry replacing it.
            
        Raises:
            ValueError: If old_entry_id is not found, or if it is already superseded.
        """
        old_entry = next((e for e in self.entries if e.id == old_entry_id), None)
        if not old_entry:
            raise ValueError(f"Memory entry {old_entry_id} not found.")

        if old_entry.superseded_by_id is not None:
            raise ValueError(
                f"Memory entry {old_entry_id} is already superseded by "
                f"{old_entry.superseded_by_id}. Multiple successors from the same "
                "entry are not allowed."
            )

        new_entry.supersedes_id = old_entry.id
        new_entry.version = old_entry.version + 1

        old_entry.superseded_by_id = new_entry.id
        old_entry.is_active = False

        self.entries.append(new_entry)
