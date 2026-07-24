"""Unit tests for the filesystem memory repository."""

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from engine.domain.enums import MemoryCategory
from engine.domain.memory import Memory, MemoryEntry
from engine.domain.project import Project
from engine.memory.exceptions import InvalidMemoryException, MemoryNotFoundException
from engine.memory.fs_repository import FilesystemMemoryRepository
from engine.project.fs_repository import FilesystemProjectRepository


@pytest.fixture
def project_repo(tmp_path: Path) -> FilesystemProjectRepository:
    """Fixture providing a project repository."""
    return FilesystemProjectRepository(tmp_path)


def test_fs_memory_repository_save_and_load(
    project_repo: FilesystemProjectRepository,
) -> None:
    # First create a project
    project = Project(name="Test Project", description="d", objective="o")
    project_repo.save(project)

    repo = FilesystemMemoryRepository(project_repo)
    memory = Memory(project_id=project.id)
    entry = MemoryEntry(
        project_id=memory.project_id,
        category=MemoryCategory.KNOWLEDGE,
        type="Info",
        title="T",
        content="C",
    )
    memory.add_entry(entry)

    # Save
    repo.save(memory)

    assert repo.exists(project.id) is True

    # Load
    loaded = repo.get_by_project_id(project.id)
    assert loaded is not None
    assert loaded.id == memory.id
    assert loaded.project_id == project.id
    assert len(loaded.entries) == 1
    assert loaded.entries[0].id == entry.id


def test_fs_memory_repository_not_found(
    project_repo: FilesystemProjectRepository,
) -> None:
    repo = FilesystemMemoryRepository(project_repo)
    missing_id = uuid4()

    # Exists should be false for a non-existent project/memory
    assert repo.exists(missing_id) is False
    assert repo.get_by_project_id(missing_id) is None


def test_fs_memory_repository_save_unregistered_project(
    project_repo: FilesystemProjectRepository,
) -> None:
    """Saving memory for a project the project repository doesn't know
    about must raise the domain-specific MemoryNotFoundException, matching
    the evaluation/architecture/planning repositories' identical pattern --
    not leak the underlying ProjectNotFoundException."""
    repo = FilesystemMemoryRepository(project_repo)
    memory = Memory(project_id=uuid4())

    with pytest.raises(MemoryNotFoundException):
        repo.save(memory)


def test_fs_memory_repository_corrupt_data(
    project_repo: FilesystemProjectRepository,
) -> None:
    project = Project(name="Corrupt Test", description="d", objective="o")
    project_repo.save(project)

    repo = FilesystemMemoryRepository(project_repo)

    # Manually write bad JSON
    project_path = project_repo.get_project_path(project.id)
    atlas_dir = project_path / ".atlas"
    atlas_dir.mkdir(exist_ok=True)
    (atlas_dir / "memory.json").write_text("invalid json")

    with pytest.raises(InvalidMemoryException, match="Failed to read or parse"):
        repo.get_by_project_id(project.id)


def test_fs_memory_repository_os_error_save(
    project_repo: FilesystemProjectRepository,
) -> None:
    project = Project(name="OS Error Save", description="d", objective="o")
    project_repo.save(project)

    repo = FilesystemMemoryRepository(project_repo)
    memory = Memory(project_id=project.id)

    # Make .atlas a file to trigger OSError when mkdir is called
    project_path = project_repo.get_project_path(project.id)
    shutil.rmtree(project_path / ".atlas")
    (project_path / ".atlas").write_text("not a folder")

    with pytest.raises(InvalidMemoryException, match="Failed to write"):
        repo.save(memory)
