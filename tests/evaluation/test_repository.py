from pathlib import Path
from uuid import uuid4

import pytest

from engine.domain.evaluation import Evaluation
from engine.domain.project import Project
from engine.evaluation.exceptions import (
    EvaluationNotFoundException,
    InvalidEvaluationException,
)
from engine.evaluation.fs_repository import FilesystemEvaluationRepository
from engine.project.fs_repository import FilesystemProjectRepository


@pytest.fixture
def repos(
    tmp_path: Path,
) -> tuple[FilesystemProjectRepository, FilesystemEvaluationRepository]:
    """Provide a filesystem project repo and evaluation repository."""
    project_repo = FilesystemProjectRepository(tmp_path)
    evaluation_repo = FilesystemEvaluationRepository(project_repo)
    return project_repo, evaluation_repo


def test_repository_save_and_get(
    repos: tuple[FilesystemProjectRepository, FilesystemEvaluationRepository],
) -> None:
    project_repo, evaluation_repo = repos

    # Create and save project
    project = Project(name="Test Project", description="d", objective="o")
    project_repo.save(project)

    res_snap_id = uuid4()
    plan_snap_id = uuid4()
    arch_snap_id = uuid4()

    # Initialize and save evaluation
    eval_obj = Evaluation(
        project_id=project.id,
        research_snapshot_id=res_snap_id,
        planning_snapshot_id=plan_snap_id,
        architecture_snapshot_id=arch_snap_id,
    )
    evaluation_repo.save(eval_obj)

    # Verify exists
    assert evaluation_repo.exists(project.id) is True

    # Retrieve and check
    retrieved = evaluation_repo.get_by_project_id(project.id)
    assert retrieved is not None
    assert retrieved.project_id == project.id
    assert retrieved.research_snapshot_id == res_snap_id


def test_repository_get_nonexistent(
    repos: tuple[FilesystemProjectRepository, FilesystemEvaluationRepository],
) -> None:
    _, evaluation_repo = repos
    # Project unregistered
    assert evaluation_repo.get_by_project_id(uuid4()) is None


def test_repository_save_unregistered_project(
    repos: tuple[FilesystemProjectRepository, FilesystemEvaluationRepository],
) -> None:
    _, evaluation_repo = repos
    eval_obj = Evaluation(
        project_id=uuid4(),
        research_snapshot_id=uuid4(),
        planning_snapshot_id=uuid4(),
        architecture_snapshot_id=uuid4(),
    )

    with pytest.raises(EvaluationNotFoundException):
        evaluation_repo.save(eval_obj)


def test_repository_corrupt_file(
    repos: tuple[FilesystemProjectRepository, FilesystemEvaluationRepository],
) -> None:
    project_repo, evaluation_repo = repos

    project = Project(name="Test Project", description="d", objective="o")
    project_repo.save(project)

    # Write corrupt JSON
    project_path = project_repo.get_project_path(project.id)
    file_path = project_path / ".atlas" / "evaluation.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as f:
        f.write("{invalid json...")

    with pytest.raises(InvalidEvaluationException):
        evaluation_repo.get_by_project_id(project.id)
