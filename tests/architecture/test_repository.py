from pathlib import Path
from uuid import uuid4

import pytest

from engine.architecture.exceptions import (
    ArchitectureNotFoundException,
    InvalidArchitectureException,
)
from engine.architecture.fs_repository import FilesystemArchitectureRepository
from engine.domain.architecture import Architecture
from engine.domain.project import Project
from engine.project.fs_repository import FilesystemProjectRepository


@pytest.fixture
def repos(tmp_path: Path) -> tuple[FilesystemProjectRepository, FilesystemArchitectureRepository]:
    """Provide a filesystem project repo and architecture repository."""
    project_repo = FilesystemProjectRepository(tmp_path)
    architecture_repo = FilesystemArchitectureRepository(project_repo)
    return project_repo, architecture_repo


def test_repository_save_and_get(
    repos: tuple[FilesystemProjectRepository, FilesystemArchitectureRepository]
) -> None:
    project_repo, architecture_repo = repos

    # Create and save project
    project = Project(name="Test Project", description="d", objective="o")
    project_repo.save(project)

    # Initialize and save architecture
    arch = Architecture(project_id=project.id, design_summary="Design pattern")
    architecture_repo.save(arch)

    # Verify exists
    assert architecture_repo.exists(project.id) is True

    # Retrieve and check
    retrieved = architecture_repo.get_by_project_id(project.id)
    assert retrieved is not None
    assert retrieved.project_id == project.id
    assert retrieved.design_summary == "Design pattern"


def test_repository_get_nonexistent(
    repos: tuple[FilesystemProjectRepository, FilesystemArchitectureRepository]
) -> None:
    _, architecture_repo = repos
    # Project unregistered
    assert architecture_repo.get_by_project_id(uuid4()) is None


def test_repository_save_unregistered_project(
    repos: tuple[FilesystemProjectRepository, FilesystemArchitectureRepository]
) -> None:
    _, architecture_repo = repos
    arch = Architecture(project_id=uuid4())

    with pytest.raises(ArchitectureNotFoundException):
        architecture_repo.save(arch)


def test_repository_corrupt_file(
    repos: tuple[FilesystemProjectRepository, FilesystemArchitectureRepository]
) -> None:
    project_repo, architecture_repo = repos

    project = Project(name="Test Project", description="d", objective="o")
    project_repo.save(project)

    # Write corrupt JSON
    project_path = project_repo.get_project_path(project.id)
    file_path = project_path / ".atlas" / "architecture.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as f:
        f.write("{invalid json...")

    with pytest.raises(InvalidArchitectureException):
        architecture_repo.get_by_project_id(project.id)
