"""Tests for project-related commands in the Application Layer."""

import uuid

import pytest

from atlas import Atlas
from atlas.commands import (
    ArchiveProjectCommand,
    CreateProjectCommand,
    ListProjectsCommand,
    LoadProjectCommand,
)
from atlas.exceptions import ProjectNotFoundError
from atlas.types import ProjectStatus

EXPECTED_PROJECT_COUNT = 2


def test_create_and_load_project(test_atlas_platform: Atlas) -> None:
    """Test creating and loading a project via the public API."""
    # Create
    cmd = CreateProjectCommand(
        name="Test Project",
        description="A test description.",
        objective="To verify the public API.",
    )
    result = test_atlas_platform.create_project(cmd)

    assert result.name == "Test Project"
    assert result.status == ProjectStatus.INITIALIZED

    # Load
    load_cmd = LoadProjectCommand(project_id=result.id)
    load_result = test_atlas_platform.load_project(load_cmd)

    assert load_result.id == result.id
    assert load_result.name == "Test Project"
    assert load_result.status == ProjectStatus.INITIALIZED


def test_list_projects(test_atlas_platform: Atlas) -> None:
    """Test listing all projects."""
    cmd1 = CreateProjectCommand(name="P1", description="D1", objective="O1")
    cmd2 = CreateProjectCommand(name="P2", description="D2", objective="O2")

    test_atlas_platform.create_project(cmd1)
    test_atlas_platform.create_project(cmd2)

    list_result = test_atlas_platform.list_projects(ListProjectsCommand())
    assert len(list_result.projects) == EXPECTED_PROJECT_COUNT
    names = {p.name for p in list_result.projects}
    assert "P1" in names
    assert "P2" in names


def test_archive_project(test_atlas_platform: Atlas) -> None:
    """Test archiving a project."""
    cmd = CreateProjectCommand(name="Archivable", description="D", objective="O")
    proj = test_atlas_platform.create_project(cmd)

    archive_cmd = ArchiveProjectCommand(project_id=proj.id)
    op_res = test_atlas_platform.archive_project(archive_cmd)

    assert op_res.success is True

    load_cmd = LoadProjectCommand(project_id=proj.id)
    load_result = test_atlas_platform.load_project(load_cmd)
    assert load_result.status == ProjectStatus.ARCHIVED


def test_load_nonexistent_project(test_atlas_platform: Atlas) -> None:
    """Test explicitly mapping internal exceptions to ProjectNotFoundError."""
    cmd = LoadProjectCommand(project_id=uuid.uuid4())

    with pytest.raises(ProjectNotFoundError):
        test_atlas_platform.load_project(cmd)
