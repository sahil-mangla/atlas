"""Unit tests for the filesystem Research repository.

S-03: Repository now stores per-project data at <project>/.atlas/research.json.
S-02: Corrupt files raise InvalidResearchException; missing files return None.
"""

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from engine.domain.project import Project
from engine.domain.research import Research
from engine.project.fs_repository import FilesystemProjectRepository
from engine.research.exceptions import InvalidResearchException
from engine.research.fs_repository import FilesystemResearchRepository


@pytest.fixture
def project_repo(tmp_path: Path) -> FilesystemProjectRepository:
    """Fixture providing a project repository backed by a temp directory."""
    return FilesystemProjectRepository(tmp_path)


@pytest.fixture
def repos(
    project_repo: FilesystemProjectRepository,
) -> tuple[FilesystemProjectRepository, FilesystemResearchRepository]:
    """Fixture providing both repos with a shared project registry."""
    research_repo = FilesystemResearchRepository(project_repo)
    return project_repo, research_repo


def test_repository_save_and_get(
    repos: tuple[FilesystemProjectRepository, FilesystemResearchRepository],
) -> None:
    """S-03: Research is stored at <project>/.atlas/research.json."""
    project_repo, research_repo = repos

    project = Project(name="Research Project", description="d", objective="o")
    project_repo.save(project)

    research = Research(project_id=project.id)
    research_repo.save(research)

    # Verify physical file location (per-project isolation)
    project_path = project_repo.get_project_path(project.id)
    assert (project_path / ".atlas" / "research.json").is_file()

    # Round-trip
    loaded = research_repo.get_by_project_id(project.id)
    assert loaded is not None
    assert loaded.id == research.id
    assert loaded.project_id == project.id


def test_repository_exists(
    repos: tuple[FilesystemProjectRepository, FilesystemResearchRepository],
) -> None:
    project_repo, research_repo = repos

    project = Project(name="Exists Project", description="d", objective="o")
    project_repo.save(project)

    assert not research_repo.exists(project.id)

    research_repo.save(Research(project_id=project.id))
    assert research_repo.exists(project.id)


def test_repository_get_not_found(
    repos: tuple[FilesystemProjectRepository, FilesystemResearchRepository],
) -> None:
    _, research_repo = repos
    assert research_repo.get_by_project_id(uuid4()) is None


def test_repository_exists_unregistered_project(
    repos: tuple[FilesystemProjectRepository, FilesystemResearchRepository],
) -> None:
    """S-03: Unregistered project returns False, not an error."""
    _, research_repo = repos
    assert research_repo.exists(uuid4()) is False


def test_repository_corrupt_file_raises(
    repos: tuple[FilesystemProjectRepository, FilesystemResearchRepository],
) -> None:
    """S-02: A corrupt research.json raises InvalidResearchException."""
    project_repo, research_repo = repos

    project = Project(name="Corrupt Test", description="d", objective="o")
    project_repo.save(project)

    # Write invalid JSON directly to the file location
    project_path = project_repo.get_project_path(project.id)
    atlas_dir = project_path / ".atlas"
    atlas_dir.mkdir(exist_ok=True)
    (atlas_dir / "research.json").write_text("not valid json", encoding="utf-8")

    with pytest.raises(InvalidResearchException, match="Failed to read or parse"):
        research_repo.get_by_project_id(project.id)


def test_repository_os_error_on_save(
    repos: tuple[FilesystemProjectRepository, FilesystemResearchRepository],
) -> None:
    """S-02: OSError during save raises InvalidResearchException."""
    project_repo, research_repo = repos

    project = Project(name="OS Error Save", description="d", objective="o")
    project_repo.save(project)

    # Block write by making .atlas a file instead of a directory
    project_path = project_repo.get_project_path(project.id)
    shutil.rmtree(project_path / ".atlas")
    (project_path / ".atlas").write_text("not a folder", encoding="utf-8")

    with pytest.raises(InvalidResearchException, match="Failed to write"):
        research_repo.save(Research(project_id=project.id))
