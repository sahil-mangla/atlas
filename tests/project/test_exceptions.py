import pytest

from engine.project.exceptions import (
    InvalidProjectException,
    ProjectAlreadyExistsException,
    ProjectException,
    ProjectLifecycleException,
    ProjectNotFoundException,
)


def test_exception_hierarchy() -> None:
    assert issubclass(ProjectException, Exception)
    assert issubclass(ProjectNotFoundException, ProjectException)
    assert issubclass(ProjectAlreadyExistsException, ProjectException)
    assert issubclass(InvalidProjectException, ProjectException)
    assert issubclass(ProjectLifecycleException, ProjectException)


def test_raise_exceptions() -> None:
    with pytest.raises(ProjectNotFoundException):
        raise ProjectNotFoundException("Not found")

    with pytest.raises(ProjectAlreadyExistsException):
        raise ProjectAlreadyExistsException("Already exists")
