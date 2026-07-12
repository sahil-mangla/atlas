"""Unit tests for the memory domain models."""

from uuid import uuid4

import pytest

from engine.domain.enums import MemoryCategory
from engine.domain.memory import Memory, MemoryEntry


def test_memory_entry_default_values() -> None:
    project_id = uuid4()
    entry = MemoryEntry(
        project_id=project_id,
        category=MemoryCategory.DECISION,
        type="Architecture Decision",
        title="Test Entry",
        content="Test content",
    )

    assert entry.project_id == project_id
    assert entry.origin == ""
    assert entry.tags == []
    assert entry.confidence == 1.0
    assert entry.version == 1
    assert entry.is_active is True
    assert entry.supersedes_id is None
    assert entry.superseded_by_id is None
    assert entry.created_at is not None


def test_memory_add_entry() -> None:
    memory = Memory(project_id=uuid4())
    entry = MemoryEntry(
        project_id=memory.project_id,
        category=MemoryCategory.KNOWLEDGE,
        type="Constraint",
        title="Must run offline",
        content="System must work without internet access.",
    )

    memory.add_entry(entry)
    assert len(memory.entries) == 1
    assert memory.entries[0] == entry

    active = memory.get_active_entries()
    assert len(active) == 1
    assert active[0] == entry


def test_memory_version_entry() -> None:
    memory = Memory(project_id=uuid4())
    entry_v1 = MemoryEntry(
        project_id=memory.project_id,
        category=MemoryCategory.ARTIFACT,
        type="Specification",
        title="Spec",
        content="V1",
    )
    memory.add_entry(entry_v1)

    entry_v2 = MemoryEntry(
        project_id=memory.project_id,
        category=MemoryCategory.ARTIFACT,
        type="Specification",
        title="Spec",
        content="V2",
    )

    memory.version_entry(entry_v1.id, entry_v2)

    assert len(memory.entries) == 2
    assert entry_v1.is_active is False
    assert entry_v1.superseded_by_id == entry_v2.id

    assert entry_v2.is_active is True
    assert entry_v2.version == 2
    assert entry_v2.supersedes_id == entry_v1.id

    active = memory.get_active_entries()
    assert len(active) == 1
    assert active[0] == entry_v2


def test_memory_version_entry_not_found() -> None:
    memory = Memory(project_id=uuid4())
    entry_v2 = MemoryEntry(
        project_id=memory.project_id,
        category=MemoryCategory.ARTIFACT,
        type="Specification",
        title="Spec",
        content="V2",
    )

    with pytest.raises(ValueError, match="not found"):
        memory.version_entry(uuid4(), entry_v2)


def test_memory_version_entry_multiple_successors_forbidden() -> None:
    memory = Memory(project_id=uuid4())
    entry_v1 = MemoryEntry(
        project_id=memory.project_id,
        category=MemoryCategory.ARTIFACT,
        type="Specification",
        title="Spec",
        content="V1",
    )
    memory.add_entry(entry_v1)

    entry_v2 = MemoryEntry(
        project_id=memory.project_id,
        category=MemoryCategory.ARTIFACT,
        type="Specification",
        title="Spec",
        content="V2",
    )
    memory.version_entry(entry_v1.id, entry_v2)

    # Try to version v1 again (branching history is forbidden by requirements)
    entry_v2_alt = MemoryEntry(
        project_id=memory.project_id,
        category=MemoryCategory.ARTIFACT,
        type="Specification",
        title="Spec",
        content="V2 Alt",
    )
    with pytest.raises(ValueError, match="already superseded"):
        memory.version_entry(entry_v1.id, entry_v2_alt)
