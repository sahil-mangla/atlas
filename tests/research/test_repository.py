from pathlib import Path
from uuid import uuid4

import pytest

from engine.domain.research import Research
from engine.research.fs_repository import FilesystemResearchRepository


@pytest.fixture
def repo(tmp_path: Path) -> FilesystemResearchRepository:
    return FilesystemResearchRepository(tmp_path)


def test_repository_save_and_get(repo: FilesystemResearchRepository) -> None:
    project_id = uuid4()
    research = Research(project_id=project_id)

    repo.save(research)

    loaded = repo.get_by_project_id(project_id)
    assert loaded is not None
    assert loaded.id == research.id
    assert loaded.project_id == project_id


def test_repository_exists(repo: FilesystemResearchRepository) -> None:
    project_id = uuid4()
    assert not repo.exists(project_id)

    research = Research(project_id=project_id)
    repo.save(research)

    assert repo.exists(project_id)


def test_repository_get_not_found(repo: FilesystemResearchRepository) -> None:
    assert repo.get_by_project_id(uuid4()) is None
