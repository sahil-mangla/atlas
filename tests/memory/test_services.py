"""Unit tests for the memory subsystem services."""

from uuid import UUID, uuid4

import pytest

from engine.domain.enums import MemoryCategory
from engine.domain.memory import Memory, MemoryEntry
from engine.memory.exceptions import MemoryNotFoundException
from engine.memory.repository import MemoryRepository
from engine.memory.services import (
    MemoryCaptureService,
    MemoryOrganizationService,
    MemoryRetrievalService,
    MemoryVersioningService,
)


class FakeMemoryRepository(MemoryRepository):
    def __init__(self) -> None:
        self.memories: dict[str, Memory] = {}

    def save(self, memory: Memory) -> None:
        self.memories[str(memory.project_id)] = memory

    def get_by_project_id(self, project_id: UUID) -> Memory | None:
        return self.memories.get(str(project_id))

    def exists(self, project_id: UUID) -> bool:
        return str(project_id) in self.memories


@pytest.fixture
def repo() -> FakeMemoryRepository:
    return FakeMemoryRepository()


def test_memory_capture_service(repo: FakeMemoryRepository) -> None:
    service = MemoryCaptureService(repo)
    project_id = uuid4()
    entry = MemoryEntry(
        project_id=project_id,
        category=MemoryCategory.DECISION,
        type="Arch",
        title="T",
        content="C",
    )

    saved = service.add_entry(project_id, entry)
    assert saved.id == entry.id
    assert repo.exists(project_id)


def test_memory_versioning_service(repo: FakeMemoryRepository) -> None:
    capture = MemoryCaptureService(repo)
    versioning = MemoryVersioningService(repo)
    project_id = uuid4()

    entry_v1 = MemoryEntry(
        project_id=project_id,
        category=MemoryCategory.ARTIFACT,
        type="Spec",
        title="T",
        content="V1",
    )
    capture.add_entry(project_id, entry_v1)

    entry_v2 = MemoryEntry(
        project_id=project_id,
        category=MemoryCategory.ARTIFACT,
        type="Spec",
        title="T",
        content="V2",
    )

    versioned = versioning.supersede_entry(project_id, entry_v1.id, entry_v2)
    assert versioned.version == 2  # noqa: PLR2004
    assert versioned.is_active is True
    assert versioned.supersedes_id == entry_v1.id

    memory = repo.get_by_project_id(project_id)
    assert memory is not None
    assert memory.entries[0].is_active is False
    assert memory.entries[0].superseded_by_id == versioned.id


def test_memory_versioning_service_not_found(repo: FakeMemoryRepository) -> None:
    versioning = MemoryVersioningService(repo)
    project_id = uuid4()

    entry_v2 = MemoryEntry(
        project_id=project_id,
        category=MemoryCategory.ARTIFACT,
        type="Spec",
        title="T",
        content="V2",
    )

    with pytest.raises(MemoryNotFoundException):
        versioning.supersede_entry(project_id, uuid4(), entry_v2)


def test_memory_retrieval_service(repo: FakeMemoryRepository) -> None:
    capture = MemoryCaptureService(repo)
    versioning = MemoryVersioningService(repo)
    retrieval = MemoryRetrievalService(repo)
    project_id = uuid4()

    entry_v1 = MemoryEntry(
        project_id=project_id,
        category=MemoryCategory.CONTEXT,
        type="T",
        title="T",
        content="V1",
    )
    capture.add_entry(project_id, entry_v1)

    entry_v2 = MemoryEntry(
        project_id=project_id,
        category=MemoryCategory.CONTEXT,
        type="T",
        title="T",
        content="V2",
    )
    versioning.supersede_entry(project_id, entry_v1.id, entry_v2)

    # Active
    active = retrieval.get_active_entries(project_id)
    assert len(active) == 1
    assert active[0].id == entry_v2.id

    # History
    history = retrieval.get_entry_history(project_id, entry_v2.id)
    assert len(history) == 2  # noqa: PLR2004
    assert history[0].id == entry_v2.id
    assert history[1].id == entry_v1.id


def test_memory_retrieval_service_exceptions(repo: FakeMemoryRepository) -> None:
    retrieval = MemoryRetrievalService(repo)
    with pytest.raises(MemoryNotFoundException):
        retrieval.get_active_entries(uuid4())

    with pytest.raises(MemoryNotFoundException):
        retrieval.get_entry_history(uuid4(), uuid4())

    # Test valid memory but entry not found
    memory = Memory(project_id=uuid4())
    repo.save(memory)
    with pytest.raises(ValueError):
        retrieval.get_entry_history(memory.project_id, uuid4())


def test_memory_organization_service(repo: FakeMemoryRepository) -> None:
    capture = MemoryCaptureService(repo)
    org = MemoryOrganizationService(repo)
    project_id = uuid4()

    e1 = MemoryEntry(
        project_id=project_id,
        category=MemoryCategory.KNOWLEDGE,
        type="Lesson",
        title="T1",
        content="C1",
    )
    e2 = MemoryEntry(
        project_id=project_id,
        category=MemoryCategory.DECISION,
        type="Arch",
        title="T2",
        content="C2",
    )
    capture.add_entry(project_id, e1)
    capture.add_entry(project_id, e2)

    knowledge = org.filter_active_by_category(project_id, MemoryCategory.KNOWLEDGE)
    assert len(knowledge) == 1
    assert knowledge[0].id == e1.id

    lesson = org.filter_active_by_type(project_id, MemoryCategory.KNOWLEDGE, "Lesson")
    assert len(lesson) == 1
    assert lesson[0].id == e1.id

    missing = org.filter_active_by_type(project_id, MemoryCategory.KNOWLEDGE, "Missing")
    assert len(missing) == 0


def test_memory_organization_service_exceptions(repo: FakeMemoryRepository) -> None:
    org = MemoryOrganizationService(repo)
    with pytest.raises(MemoryNotFoundException):
        org.filter_active_by_category(uuid4(), MemoryCategory.KNOWLEDGE)
