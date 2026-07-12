"""Serialization logic for the ATLAS Memory System."""

from typing import Any

from engine.domain.enums import MemoryCategory
from engine.domain.memory import Memory, MemoryEntry


def serialize_entry(entry: MemoryEntry) -> dict[str, Any]:
    """Serialize a MemoryEntry into a dictionary."""
    return {
        "id": str(entry.id),
        "project_id": str(entry.project_id),
        "category": entry.category.value,
        "type": entry.type,
        "title": entry.title,
        "content": entry.content,
        "origin": entry.origin,
        "tags": entry.tags,
        "confidence": entry.confidence,
        "version": entry.version,
        "is_active": entry.is_active,
        "supersedes_id": str(entry.supersedes_id) if entry.supersedes_id else None,
        "superseded_by_id": (
            str(entry.superseded_by_id) if entry.superseded_by_id else None
        ),
        "created_at": entry.created_at.isoformat(),
    }


def deserialize_entry(data: dict[str, Any]) -> MemoryEntry:
    """Deserialize a dictionary into a MemoryEntry."""
    # Convert category back to enum if necessary, Pydantic handles str to enum usually
    # But it's safer to pass exactly what's needed.
    return MemoryEntry(
        id=data["id"],
        project_id=data["project_id"],
        category=MemoryCategory(data["category"]),
        type=data["type"],
        title=data["title"],
        content=data["content"],
        origin=data.get("origin", ""),
        tags=data.get("tags", []),
        confidence=data.get("confidence", 1.0),
        version=data.get("version", 1),
        is_active=data.get("is_active", True),
        supersedes_id=data.get("supersedes_id"),
        superseded_by_id=data.get("superseded_by_id"),
        created_at=data["created_at"],
    )


def serialize_memory(memory: Memory) -> dict[str, Any]:
    """Serialize a Memory aggregate root into a dictionary."""
    return {
        "id": str(memory.id),
        "project_id": str(memory.project_id),
        "entries": [serialize_entry(e) for e in memory.entries],
    }


def deserialize_memory(data: dict[str, Any]) -> Memory:
    """Deserialize a dictionary into a Memory aggregate root."""
    entries = [deserialize_entry(e) for e in data.get("entries", [])]
    return Memory(
        id=data["id"],
        project_id=data["project_id"],
        entries=entries,
    )
