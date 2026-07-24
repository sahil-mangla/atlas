"""Filesystem implementation of the WorkflowRepository."""

import json
from uuid import UUID

from engine.domain.workflow import Workflow
from engine.project.exceptions import ProjectNotFoundException
from engine.project.repository import ProjectRepository
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowNotFoundException,
)
from engine.workflow.repository import WorkflowRepository
from engine.workflow.serializers import deserialize_workflow, serialize_workflow
from shared.atomic_write import atomic_write_text


class FilesystemWorkflowRepository(WorkflowRepository):
    """Filesystem-backed implementation of WorkflowRepository.

    Stores workflow state as a JSON file within the project's .atlas/ directory.
    """

    def __init__(self, project_repo: ProjectRepository) -> None:
        self.project_repo = project_repo

    def save(self, workflow: Workflow) -> None:
        """Save the workflow state to persistence."""
        try:
            project_path = self.project_repo.get_project_path(workflow.project_id)
        except ProjectNotFoundException as e:
            raise WorkflowNotFoundException(
                f"Project {workflow.project_id} not tracked by repository."
            ) from e

        atlas_dir = project_path / ".atlas"
        workflow_file = atlas_dir / "workflow.json"

        try:
            atlas_dir.mkdir(parents=True, exist_ok=True)
            data = serialize_workflow(workflow)
            atomic_write_text(workflow_file, json.dumps(data, indent=2))
        except OSError as e:
            raise InvalidTransitionException(
                f"Failed to write workflow data to {workflow_file}: {e}"
            ) from e

    def get_by_project_id(self, project_id: UUID) -> Workflow | None:
        """Retrieve the workflow state for a specific project."""
        try:
            project_path = self.project_repo.get_project_path(project_id)
        except ProjectNotFoundException:
            return None

        workflow_file = project_path / ".atlas" / "workflow.json"

        if not workflow_file.is_file():
            return None

        try:
            with workflow_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return deserialize_workflow(data)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            raise InvalidTransitionException(
                f"Failed to read or parse workflow from {workflow_file}: {e}"
            ) from e

    def exists(self, project_id: UUID) -> bool:
        """Check if workflow state exists for a specific project."""
        try:
            project_path = self.project_repo.get_project_path(project_id)
            workflow_file = project_path / ".atlas" / "workflow.json"
            return workflow_file.is_file()
        except ProjectNotFoundException:
            return False
