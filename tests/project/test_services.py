from pathlib import Path
from uuid import uuid4

import pytest

from engine.domain.enums import ProjectStatus, WorkflowStage
from engine.project.exceptions import (
    ProjectException,
    ProjectLifecycleException,
    ProjectNotFoundException,
)
from engine.project.fs_repository import FilesystemProjectRepository
from engine.project.services import (
    ProjectCreationService,
    ProjectLifecycleService,
    ProjectLoadingService,
    ProjectRegistryService,
)


@pytest.fixture
def repo(tmp_path: Path) -> FilesystemProjectRepository:
    return FilesystemProjectRepository(tmp_path)


def test_creation_service(repo: FilesystemProjectRepository) -> None:
    service = ProjectCreationService(repo)

    # Success creation
    project = service.create_project(
        name="My New Project",
        description="A cool project description",
        objective="To build cool things",
    )
    assert project.name == "My New Project"
    assert project.status == ProjectStatus.INITIALIZED
    assert project.current_stage == WorkflowStage.IDEA

    # Empty name failure
    with pytest.raises(ProjectException, match="Project name cannot be empty"):
        service.create_project(
            name="   ",
            description="desc",
            objective="obj",
        )


def test_creation_service_custom_path(
    repo: FilesystemProjectRepository, tmp_path: Path
) -> None:
    service = ProjectCreationService(repo)
    custom_path = tmp_path / "somewhere" / "else"
    project = service.create_project(
        name="Path Project",
        description="d",
        objective="o",
        path=custom_path,
    )
    assert repo.get_project_path(project.id) == custom_path


def test_loading_service(repo: FilesystemProjectRepository) -> None:
    creation = ProjectCreationService(repo)
    loading = ProjectLoadingService(repo)

    project = creation.create_project(name="Load Test", description="d", objective="o")

    # Load success
    loaded = loading.load_project(project.id)
    assert loaded.id == project.id
    assert loaded.name == "Load Test"

    # Load missing
    with pytest.raises(ProjectNotFoundException):
        loading.load_project(uuid4())


def test_registry_service(repo: FilesystemProjectRepository) -> None:
    creation = ProjectCreationService(repo)
    registry = ProjectRegistryService(repo)

    assert len(registry.list_projects()) == 0

    p1 = creation.create_project(name="Proj 1", description="d", objective="o")
    p2 = creation.create_project(name="Proj 2", description="d", objective="o")

    projects = registry.list_projects()
    expected_count = 2
    assert len(projects) == expected_count
    ids = {p.id for p in projects}
    assert p1.id in ids
    assert p2.id in ids


def test_lifecycle_service_metadata_update(
    repo: FilesystemProjectRepository,
) -> None:
    creation = ProjectCreationService(repo)
    lifecycle = ProjectLifecycleService(repo)

    project = creation.create_project(
        name="Metadata Test", description="d", objective="o"
    )

    # Update metadata success
    updated = lifecycle.update_metadata(
        project.id,
        name="Updated Name",
        description="Updated Desc",
        objective="Updated Obj",
    )
    assert updated.name == "Updated Name"
    assert updated.description == "Updated Desc"
    assert updated.objective == "Updated Obj"

    # Update name to empty failure
    with pytest.raises(ProjectException):
        lifecycle.update_metadata(project.id, name="")


def test_lifecycle_service_status_update(
    repo: FilesystemProjectRepository,
) -> None:
    creation = ProjectCreationService(repo)
    lifecycle = ProjectLifecycleService(repo)

    project = creation.create_project(
        name="Status Test", description="d", objective="o"
    )

    # Update status success
    updated = lifecycle.update_status(project.id, ProjectStatus.ACTIVE)
    assert updated.status == ProjectStatus.ACTIVE


def test_lifecycle_service_archive(repo: FilesystemProjectRepository) -> None:
    creation = ProjectCreationService(repo)
    lifecycle = ProjectLifecycleService(repo)

    project = creation.create_project(
        name="Archive Test", description="d", objective="o"
    )

    # Archive project
    archived = lifecycle.archive_project(project.id)
    assert archived.status == ProjectStatus.ARCHIVED

    # Archiving again is idempotent and doesn't fail
    archived2 = lifecycle.archive_project(project.id)
    assert archived2.status == ProjectStatus.ARCHIVED


def test_lifecycle_service_archived_locks(
    repo: FilesystemProjectRepository,
) -> None:
    creation = ProjectCreationService(repo)
    lifecycle = ProjectLifecycleService(repo)

    project = creation.create_project(name="Lock Test", description="d", objective="o")
    lifecycle.archive_project(project.id)

    # Attempting to update metadata on archived project raises ProjectLifecycleException
    with pytest.raises(ProjectLifecycleException):
        lifecycle.update_metadata(project.id, name="Fail Name")

    # Attempting to update status on archived project raises ProjectLifecycleException
    with pytest.raises(ProjectLifecycleException):
        lifecycle.update_status(project.id, ProjectStatus.ACTIVE)


def test_lifecycle_service_not_found(repo: FilesystemProjectRepository) -> None:
    lifecycle = ProjectLifecycleService(repo)
    missing_id = uuid4()

    with pytest.raises(ProjectNotFoundException):
        lifecycle.update_metadata(missing_id, name="Name")

    with pytest.raises(ProjectNotFoundException):
        lifecycle.update_status(missing_id, ProjectStatus.ACTIVE)

    with pytest.raises(ProjectNotFoundException):
        lifecycle.archive_project(missing_id)
