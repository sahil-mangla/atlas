"""Unit tests for the filesystem Planning repository.

S-03: Repository now stores per-project data at <project>/.atlas/planning.json.
S-02: Corrupt files raise InvalidPlanningException; missing files return None.
"""

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from engine.domain.planning import Planning
from engine.domain.project import Project
from engine.planning.exceptions import InvalidPlanningException
from engine.planning.fs_repository import FilesystemPlanningRepository
from engine.project.fs_repository import FilesystemProjectRepository


@pytest.fixture
def project_repo(tmp_path: Path) -> FilesystemProjectRepository:
    return FilesystemProjectRepository(tmp_path)


@pytest.fixture
def repos(
    project_repo: FilesystemProjectRepository,
) -> tuple[FilesystemProjectRepository, FilesystemPlanningRepository]:
    planning_repo = FilesystemPlanningRepository(project_repo)
    return project_repo, planning_repo


def test_repository_save_and_get(
    repos: tuple[FilesystemProjectRepository, FilesystemPlanningRepository],
) -> None:
    """S-03: Planning is stored at <project>/.atlas/planning.json."""
    project_repo, planning_repo = repos

    project = Project(name="Planning Project", description="d", objective="o")
    project_repo.save(project)

    planning = Planning(project_id=project.id)
    planning_repo.save(planning)

    # Verify physical file location (per-project isolation)
    project_path = project_repo.get_project_path(project.id)
    assert (project_path / ".atlas" / "planning.json").is_file()

    # Round-trip
    loaded = planning_repo.get_by_project_id(project.id)
    assert loaded is not None
    assert loaded.id == planning.id
    assert loaded.project_id == project.id


def test_repository_exists(
    repos: tuple[FilesystemProjectRepository, FilesystemPlanningRepository],
) -> None:
    project_repo, planning_repo = repos

    project = Project(name="Exists Project", description="d", objective="o")
    project_repo.save(project)

    assert not planning_repo.exists(project.id)

    planning_repo.save(Planning(project_id=project.id))
    assert planning_repo.exists(project.id)


def test_repository_get_not_found(
    repos: tuple[FilesystemProjectRepository, FilesystemPlanningRepository],
) -> None:
    _, planning_repo = repos
    assert planning_repo.get_by_project_id(uuid4()) is None


def test_repository_exists_unregistered_project(
    repos: tuple[FilesystemProjectRepository, FilesystemPlanningRepository],
) -> None:
    """S-03: An unregistered project ID returns False from exists()."""
    _, planning_repo = repos
    assert planning_repo.exists(uuid4()) is False


def test_repository_corrupt_file_raises(
    repos: tuple[FilesystemProjectRepository, FilesystemPlanningRepository],
) -> None:
    """S-02: A corrupt planning.json raises InvalidPlanningException."""
    project_repo, planning_repo = repos

    project = Project(name="Corrupt Test", description="d", objective="o")
    project_repo.save(project)

    project_path = project_repo.get_project_path(project.id)
    atlas_dir = project_path / ".atlas"
    atlas_dir.mkdir(exist_ok=True)
    (atlas_dir / "planning.json").write_text("not valid json", encoding="utf-8")

    with pytest.raises(InvalidPlanningException, match="Failed to read or parse"):
        planning_repo.get_by_project_id(project.id)


def test_repository_os_error_on_save(
    repos: tuple[FilesystemProjectRepository, FilesystemPlanningRepository],
) -> None:
    """S-02: OSError during save raises InvalidPlanningException."""
    project_repo, planning_repo = repos

    project = Project(name="OS Error Save", description="d", objective="o")
    project_repo.save(project)

    project_path = project_repo.get_project_path(project.id)
    shutil.rmtree(project_path / ".atlas")
    (project_path / ".atlas").write_text("not a folder", encoding="utf-8")

    with pytest.raises(InvalidPlanningException, match="Failed to write"):
        planning_repo.save(Planning(project_id=project.id))
