"""Unit tests for ProjectCapability's create_project rollback behavior.

If workflow initialization fails after the project record was already
persisted, the project must not be left orphaned -- stuck forever with no
workflow, unusable, and blocking re-creation under the same name.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from atlas.capabilities.project_capability import ProjectCapability
from atlas.commands import CreateProjectCommand
from atlas.exceptions import ApplicationError
from engine.domain.project import Project


def _capability(
    project_creation_service: MagicMock, workflow_initialization_service: MagicMock
) -> ProjectCapability:
    return ProjectCapability(
        project_creation_service=project_creation_service,
        project_loading_service=MagicMock(),
        project_listing_service=MagicMock(),
        project_archive_service=MagicMock(),
        workflow_initialization_service=workflow_initialization_service,
    )


def test_create_project_rolls_back_project_when_workflow_init_fails() -> None:
    project = Project(id=uuid4(), name="P", description="d", objective="o")
    project_creation_service = MagicMock()
    project_creation_service.create_project.return_value = project
    workflow_initialization_service = MagicMock()
    workflow_initialization_service.initialize_workflow.side_effect = RuntimeError(
        "disk full"
    )

    capability = _capability(project_creation_service, workflow_initialization_service)
    command = CreateProjectCommand(name="P", description="d", objective="o")

    with pytest.raises(ApplicationError, match="rolled back"):
        capability.create_project(command)

    project_creation_service.repository.delete.assert_called_once_with(project.id)


def test_create_project_succeeds_when_workflow_init_succeeds() -> None:
    project = Project(id=uuid4(), name="P", description="d", objective="o")
    project_creation_service = MagicMock()
    project_creation_service.create_project.return_value = project
    workflow_initialization_service = MagicMock()

    capability = _capability(project_creation_service, workflow_initialization_service)
    command = CreateProjectCommand(name="P", description="d", objective="o")

    result = capability.create_project(command)

    assert result.id == project.id
    project_creation_service.repository.delete.assert_not_called()
