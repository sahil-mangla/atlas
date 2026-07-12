import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from engine.domain.project import Project
from engine.project.exceptions import (
    InvalidProjectException,
    ProjectAlreadyExistsException,
    ProjectNotFoundException,
)
from engine.project.fs_repository import FilesystemProjectRepository


def test_fs_repository_init_empty(tmp_path: Path) -> None:
    repo = FilesystemProjectRepository(tmp_path)
    assert len(repo.discover()) == 0


def test_fs_repository_save_and_load(tmp_path: Path) -> None:
    repo = FilesystemProjectRepository(tmp_path)
    project = Project(
        name="Test Project",
        description="A description",
        objective="An objective",
    )

    repo.save(project)

    # Check physical folder was created under base_dir / slug
    proj_dir = tmp_path / "test-project"
    assert proj_dir.is_dir()
    metadata_file = proj_dir / ".atlas" / "project.json"
    assert metadata_file.is_file()

    # Load from file to verify serialization structure
    with metadata_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["name"] == "Test Project"
    assert data["id"] == str(project.id)

    # Retrieve from repository
    loaded = repo.get_by_id(project.id)
    assert loaded is not None
    assert loaded.id == project.id
    assert loaded.name == "Test Project"


def test_fs_repository_load_missing(tmp_path: Path) -> None:
    repo = FilesystemProjectRepository(tmp_path)
    assert repo.get_by_id(uuid4()) is None


def test_fs_repository_corrupt_json(tmp_path: Path) -> None:
    repo = FilesystemProjectRepository(tmp_path)
    project = Project(
        name="Corrupt Project",
        description="desc",
        objective="obj",
    )
    repo.save(project)

    proj_dir = tmp_path / "corrupt-project"
    metadata_file = proj_dir / ".atlas" / "project.json"

    # Write corrupt data
    with metadata_file.open("w", encoding="utf-8") as f:
        f.write("not valid json")

    # Mypy rescans and skips corrupt folder, get_by_id raises InvalidProjectException
    with pytest.raises(InvalidProjectException):
        repo.get_by_id(project.id)


def test_fs_repository_already_exists_conflict(tmp_path: Path) -> None:
    repo = FilesystemProjectRepository(tmp_path)

    # Save first project
    project1 = Project(name="Conflict Project", description="d1", objective="o1")
    repo.save(project1)

    # Try saving second project with same name (causing same slug)
    project2 = Project(name="Conflict Project", description="d2", objective="o2")
    with pytest.raises(ProjectAlreadyExistsException):
        repo.save(project2)


def test_fs_repository_register_custom_path(tmp_path: Path) -> None:
    repo = FilesystemProjectRepository(tmp_path)
    custom_dir = tmp_path / "custom" / "my-project-location"
    project = Project(name="Custom Project", description="d", objective="o")

    repo.register_path(project.id, custom_dir)
    repo.save(project)

    assert custom_dir.is_dir()
    assert (custom_dir / ".atlas" / "project.json").is_file()

    # Verify discovery picks it up
    new_repo = FilesystemProjectRepository(tmp_path)
    assert len(new_repo.discover()) == 0  # not in base dir

    # Add custom dir's parent to verify rescan doesn't scan recursively
    # (only matches one level deep in base_dir)
    another_base = tmp_path / "custom"
    another_repo = FilesystemProjectRepository(another_base)
    discovered = another_repo.discover()
    assert len(discovered) == 1
    assert discovered[0].id == project.id


def test_fs_repository_get_project_path(tmp_path: Path) -> None:
    repo = FilesystemProjectRepository(tmp_path)
    project = Project(name="Path Test", description="d", objective="o")
    repo.save(project)

    path = repo.get_project_path(project.id)
    assert path == tmp_path / "path-test"

    # Missing project path retrieval raises ProjectNotFoundException
    with pytest.raises(ProjectNotFoundException):
        repo.get_project_path(uuid4())


def test_fs_repository_base_dir_not_exists(tmp_path: Path) -> None:
    non_existent = tmp_path / "does-not-exist"
    repo = FilesystemProjectRepository(non_existent)
    assert len(repo.discover()) == 0


def test_fs_repository_startup_skip_corrupt(tmp_path: Path) -> None:
    # Set up a project directory with corrupt project metadata
    corrupt_dir = tmp_path / "corrupt-project"
    metadata_file = corrupt_dir / ".atlas" / "project.json"
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    with metadata_file.open("w", encoding="utf-8") as f:
        f.write("{invalid json")

    # Scanner should successfully skip it on startup
    repo = FilesystemProjectRepository(tmp_path)
    assert len(repo.discover()) == 0


def test_fs_repository_load_file_os_error(tmp_path: Path) -> None:
    repo = FilesystemProjectRepository(tmp_path)
    project = Project(name="OS Error Load", description="d", objective="o")
    repo.save(project)

    # Change permissions to make it unreadable
    metadata_file = tmp_path / "os-error-load" / ".atlas" / "project.json"
    metadata_file.chmod(0o000)

    try:
        with pytest.raises(
            InvalidProjectException, match="Failed to read project metadata file"
        ):
            repo.get_by_id(project.id)
    finally:
        metadata_file.chmod(0o644)


def test_fs_repository_save_file_os_error(tmp_path: Path) -> None:
    repo = FilesystemProjectRepository(tmp_path)
    project = Project(name="OS Error Save", description="d", objective="o")
    repo.save(project)

    # Trigger OSError by making .atlas parent folder a file
    proj_dir = tmp_path / "os-error-save"
    shutil.rmtree(proj_dir)
    proj_dir.mkdir()
    # Write `.atlas` as a file
    (proj_dir / ".atlas").write_text("not a folder")

    with pytest.raises(
        InvalidProjectException, match="Failed to write project metadata"
    ):
        repo.save(project)


def test_fs_repository_deleted_externally(tmp_path: Path) -> None:
    repo = FilesystemProjectRepository(tmp_path)
    project = Project(name="External Delete", description="d", objective="o")
    repo.save(project)

    # Delete project directory externally
    proj_dir = tmp_path / "external-delete"
    shutil.rmtree(proj_dir)

    # get_by_id should clean up path mapping and return None
    assert repo.get_by_id(project.id) is None


def test_fs_repository_save_conflict_corrupt_data(tmp_path: Path) -> None:
    repo = FilesystemProjectRepository(tmp_path)

    # Pre-create directory containing corrupt config file
    proj_dir = tmp_path / "save-conflict-corrupt"
    metadata_file = proj_dir / ".atlas" / "project.json"
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    metadata_file.write_text("corrupt data")

    # Try saving a new project that slugifies to same directory
    project = Project(name="Save Conflict Corrupt", description="d", objective="o")
    with pytest.raises(
        ProjectAlreadyExistsException, match="already exists and contains corrupt"
    ):
        repo.save(project)
