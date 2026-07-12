from pathlib import Path
from uuid import uuid4

import pytest

from engine.domain.planning import Planning
from engine.planning.fs_repository import FilesystemPlanningRepository


@pytest.fixture
def repo(tmp_path: Path) -> FilesystemPlanningRepository:
    return FilesystemPlanningRepository(tmp_path)


def test_repository_save_and_get(repo: FilesystemPlanningRepository) -> None:
    project_id = uuid4()
    planning = Planning(project_id=project_id)

    repo.save(planning)

    loaded = repo.get_by_project_id(project_id)
    assert loaded is not None
    assert loaded.id == planning.id
    assert loaded.project_id == project_id


def test_repository_exists(repo: FilesystemPlanningRepository) -> None:
    project_id = uuid4()
    assert not repo.exists(project_id)

    planning = Planning(project_id=project_id)
    repo.save(planning)

    assert repo.exists(project_id)


def test_repository_get_not_found(repo: FilesystemPlanningRepository) -> None:
    assert repo.get_by_project_id(uuid4()) is None
