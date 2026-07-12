"""Unit tests for the filesystem workflow repository."""

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from engine.domain.enums import ApprovalStatus, WorkflowStage
from engine.domain.project import Project
from engine.domain.workflow import Workflow, WorkflowHistoryEntry
from engine.project.fs_repository import FilesystemProjectRepository
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowNotFoundException,
)
from engine.workflow.fs_repository import FilesystemWorkflowRepository


@pytest.fixture
def project_repo(tmp_path: Path) -> FilesystemProjectRepository:
    """Fixture providing a project repository."""
    return FilesystemProjectRepository(tmp_path)


def test_fs_workflow_repository_save_and_load(
    project_repo: FilesystemProjectRepository,
) -> None:
    project = Project(name="Test Project", description="d", objective="o")
    project_repo.save(project)

    repo = FilesystemWorkflowRepository(project_repo)
    workflow = Workflow(project_id=project.id)
    entry = WorkflowHistoryEntry(
        previous_stage=WorkflowStage.IDEA,
        new_stage=WorkflowStage.RESEARCH,
        approval_status=ApprovalStatus.APPROVED,
        reason="Proceed",
        confidence=0.9,
    )
    workflow.record_transition(entry)

    # Save
    repo.save(workflow)

    assert repo.exists(project.id) is True

    # Load
    loaded = repo.get_by_project_id(project.id)
    assert loaded is not None
    assert loaded.id == workflow.id
    assert loaded.project_id == project.id
    assert loaded.current_stage == WorkflowStage.RESEARCH
    assert len(loaded.history) == 1
    assert loaded.history[0].id == entry.id


def test_fs_workflow_repository_not_found(
    project_repo: FilesystemProjectRepository,
) -> None:
    repo = FilesystemWorkflowRepository(project_repo)
    missing_id = uuid4()

    assert repo.exists(missing_id) is False
    assert repo.get_by_project_id(missing_id) is None


def test_fs_workflow_repository_save_missing_project(
    project_repo: FilesystemProjectRepository,
) -> None:
    repo = FilesystemWorkflowRepository(project_repo)
    workflow = Workflow(project_id=uuid4())

    with pytest.raises(WorkflowNotFoundException, match="not tracked"):
        repo.save(workflow)


def test_fs_workflow_repository_corrupt_data(
    project_repo: FilesystemProjectRepository,
) -> None:
    project = Project(name="Corrupt Test", description="d", objective="o")
    project_repo.save(project)

    repo = FilesystemWorkflowRepository(project_repo)

    project_path = project_repo.get_project_path(project.id)
    atlas_dir = project_path / ".atlas"
    atlas_dir.mkdir(exist_ok=True)
    (atlas_dir / "workflow.json").write_text("invalid json")

    with pytest.raises(InvalidTransitionException, match="Failed to read or parse"):
        repo.get_by_project_id(project.id)


def test_fs_workflow_repository_os_error_save(
    project_repo: FilesystemProjectRepository,
) -> None:
    project = Project(name="OS Error Save", description="d", objective="o")
    project_repo.save(project)

    repo = FilesystemWorkflowRepository(project_repo)
    workflow = Workflow(project_id=project.id)

    # Make .atlas a file to trigger OSError when mkdir is called
    project_path = project_repo.get_project_path(project.id)
    shutil.rmtree(project_path / ".atlas")
    (project_path / ".atlas").write_text("not a folder")

    with pytest.raises(InvalidTransitionException, match="Failed to write"):
        repo.save(workflow)
