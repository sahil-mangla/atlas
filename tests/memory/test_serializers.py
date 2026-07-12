"""Unit tests for the memory serializers."""

from uuid import uuid4

from engine.domain.enums import MemoryCategory
from engine.domain.memory import Memory, MemoryEntry
from engine.memory.serializers import (
    deserialize_entry,
    deserialize_memory,
    serialize_entry,
    serialize_memory,
)


def test_serialize_and_deserialize_entry() -> None:
    entry = MemoryEntry(
        project_id=uuid4(),
        category=MemoryCategory.ARTIFACT,
        type="Diagram",
        title="Architecture Diagram",
        content="mermaid content here",
        tags=["design", "architecture"],
        confidence=0.8,
    )

    data = serialize_entry(entry)

    assert data["id"] == str(entry.id)
    assert data["category"] == "artifact"
    assert data["tags"] == ["design", "architecture"]

    deserialized = deserialize_entry(data)

    assert deserialized.id == entry.id
    assert deserialized.project_id == entry.project_id
    assert deserialized.category == entry.category
    assert deserialized.type == entry.type
    assert deserialized.title == entry.title
    assert deserialized.content == entry.content
    assert deserialized.tags == entry.tags
    assert deserialized.confidence == entry.confidence
    assert deserialized.created_at == entry.created_at


def test_serialize_and_deserialize_memory() -> None:
    memory = Memory(project_id=uuid4())
    entry = MemoryEntry(
        project_id=memory.project_id,
        category=MemoryCategory.DECISION,
        type="Arch Decision",
        title="D1",
        content="C1",
    )
    memory.add_entry(entry)

    data = serialize_memory(memory)

    assert data["id"] == str(memory.id)
    assert data["project_id"] == str(memory.project_id)
    assert len(data["entries"]) == 1

    deserialized = deserialize_memory(data)

    assert deserialized.id == memory.id
    assert deserialized.project_id == memory.project_id
    assert len(deserialized.entries) == 1
    assert deserialized.entries[0].id == entry.id
