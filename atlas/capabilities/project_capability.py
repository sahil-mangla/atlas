"""Project lifecycle capability.

Relocated verbatim from ``atlas/_service.py``'s pre-Phase-15 ``Atlas``
methods. This is a thin delegation layer -- see the Capability
Responsibility Rule in ``docs/plans/phase-15-platform-layer.md`` §3.5.
"""

from pathlib import Path

from atlas.commands import (
    ArchiveProjectCommand,
    CreateProjectCommand,
    ListProjectsCommand,
    LoadProjectCommand,
)
from atlas.exceptions import (
    ApplicationError,
    InvalidProjectError,
    ProjectAlreadyExistsError,
    ProjectLifecycleError,
    ProjectNotFoundError,
)
from atlas.results import OperationResult, ProjectListResult, ProjectResult
from atlas.types import ProjectStatus
from engine.project.exceptions import (
    InvalidProjectException,
    ProjectAlreadyExistsException,
    ProjectException,
    ProjectLifecycleException,
    ProjectNotFoundException,
)
from engine.project.services import (
    ProjectCreationService,
    ProjectLifecycleService,
    ProjectLoadingService,
    ProjectRegistryService,
)
from engine.workflow.services import WorkflowInitializationService


class ProjectCapability:
    """Project lifecycle -- creation, loading, listing, archiving."""

    def __init__(
        self,
        project_creation_service: ProjectCreationService,
        project_loading_service: ProjectLoadingService,
        project_listing_service: ProjectRegistryService,
        project_archive_service: ProjectLifecycleService,
        workflow_initialization_service: WorkflowInitializationService,
    ) -> None:
        self._project_creation_service = project_creation_service
        self._project_loading_service = project_loading_service
        self._project_listing_service = project_listing_service
        self._project_archive_service = project_archive_service
        self._workflow_initialization_service = workflow_initialization_service

    def _map_project_exception(self, e: Exception) -> ApplicationError:
        """Map internal project exceptions to application errors."""
        if isinstance(e, ProjectNotFoundException):
            return ProjectNotFoundError(str(e))
        if isinstance(e, ProjectAlreadyExistsException):
            return ProjectAlreadyExistsError(str(e))
        if isinstance(e, InvalidProjectException):
            return InvalidProjectError(str(e))
        if isinstance(e, ProjectLifecycleException):
            return ProjectLifecycleError(str(e))
        if isinstance(e, ProjectException):
            return ApplicationError(str(e))
        raise e

    def create_project(self, command: CreateProjectCommand) -> ProjectResult:
        """Initialize a new local engineering project."""
        try:
            project = self._project_creation_service.create_project(
                name=command.name,
                description=command.description,
                objective=command.objective,
                path=Path(command.path) if command.path else None,
            )
        except ProjectException as e:
            raise self._map_project_exception(e) from e

        try:
            self._workflow_initialization_service.initialize_workflow(project.id)
        except Exception as e:
            # The project record was already persisted; without this rollback
            # it would be stuck permanently -- listed, but with no workflow,
            # so every subsequent operation on it fails, and re-creating it
            # under the same name would hit ProjectAlreadyExistsError.
            self._project_creation_service.repository.delete(project.id)
            raise ApplicationError(
                "Project creation failed while initializing its workflow; "
                f"the partially created project has been rolled back. Error: {e}"
            ) from e

        return ProjectResult(
            id=project.id,
            name=project.name,
            description=project.description,
            objective=project.objective,
            status=ProjectStatus(project.status.value),
        )

    def load_project(self, command: LoadProjectCommand) -> ProjectResult:
        """Load an existing project by ID."""
        try:
            project = self._project_loading_service.load_project(command.project_id)
            return ProjectResult(
                id=project.id,
                name=project.name,
                description=project.description,
                objective=project.objective,
                status=ProjectStatus(project.status.value),
            )
        except ProjectException as e:
            raise self._map_project_exception(e) from e

    def list_projects(self, _command: ListProjectsCommand) -> ProjectListResult:
        """List all known projects."""
        try:
            projects = self._project_listing_service.list_projects()
            results = [
                ProjectResult(
                    id=p.id,
                    name=p.name,
                    description=p.description,
                    objective=p.objective,
                    status=ProjectStatus(p.status.value),
                )
                for p in projects
            ]
            return ProjectListResult(projects=results)
        except ProjectException as e:
            raise self._map_project_exception(e) from e

    def archive_project(self, command: ArchiveProjectCommand) -> OperationResult:
        """Archive a project."""
        try:
            self._project_archive_service.archive_project(command.project_id)
            return OperationResult(
                success=True, message="Project archived successfully."
            )
        except ProjectException as e:
            raise self._map_project_exception(e) from e
