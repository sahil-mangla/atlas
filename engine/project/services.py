"""Services for the ATLAS Project System."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from engine.domain.enums import ProjectStatus
from engine.domain.project import Project
from engine.project.exceptions import (
    ProjectException,
    ProjectLifecycleException,
    ProjectNotFoundException,
)
from engine.project.repository import ProjectRepository


class ProjectCreationService:
    """Service to handle the creation and initialization of new ATLAS projects."""

    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    def create_project(
        self,
        name: str,
        description: str,
        objective: str,
        path: Path | None = None,
    ) -> Project:
        """Initialize a new project, create the workspace, and persist project metadata.

        Args:
            name: The human-readable name of the project.
            description: Summary of the project goals.
            objective: High-level vision or engineering goal statement.
            path: Optional physical directory path for the project.

        Returns:
            The newly created Project domain model.

        Raises:
            ProjectException: If validation fails or creation fails.
        """
        if not name.strip():
            raise ProjectException("Project name cannot be empty.")

        project = Project(
            name=name.strip(),
            description=description.strip(),
            objective=objective.strip(),
            status=ProjectStatus.INITIALIZED,
        )

        if path:
            # Register path with the repository if it supports registering custom paths
            register_path_fn = getattr(self.repository, "register_path", None)
            if register_path_fn and callable(register_path_fn):
                register_path_fn(project.id, path)

        self.repository.save(project)
        return project


class ProjectLoadingService:
    """Service to load existing projects from the repository."""

    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    def load_project(self, project_id: UUID) -> Project:
        """Load an existing project by its unique identifier.

        Args:
            project_id: The UUID of the project.

        Returns:
            The loaded Project domain model.

        Raises:
            ProjectNotFoundException: If the project does not exist.
        """
        project = self.repository.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundException(
                f"Project with ID {project_id} could not be found."
            )
        return project


class ProjectRegistryService:
    """Service to discover and list existing ATLAS projects."""

    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    def list_projects(self) -> list[Project]:
        """Discover and return all projects present in the repository.

        Returns:
            A list of discovered Project domain models.
        """
        return self.repository.discover()


class ProjectLifecycleService:
    """Service to manage lifecycle transitions and metadata updates."""

    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    def _get_active_project(self, project_id: UUID) -> Project:
        """Helper to get a project and assert it is not archived.

        Raises:
            ProjectNotFoundException: If the project doesn't exist.
            ProjectLifecycleException: If the project is archived.
        """
        project = self.repository.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundException(
                f"Project with ID {project_id} could not be found."
            )

        if project.status == ProjectStatus.ARCHIVED:
            raise ProjectLifecycleException(
                f"Project with ID {project_id} is archived and cannot be modified."
            )

        return project

    def archive_project(self, project_id: UUID) -> Project:
        """Archive a project, making it read-only.

        Args:
            project_id: The UUID of the project.

        Returns:
            The archived Project domain model.
        """
        # We allow loading the project even if it's already archived without throwing.
        project = self.repository.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundException(
                f"Project with ID {project_id} could not be found."
            )

        if project.status == ProjectStatus.ARCHIVED:
            return project

        project.status = ProjectStatus.ARCHIVED
        project.updated_at = datetime.now(UTC)
        self.repository.save(project)
        return project

    def update_metadata(
        self,
        project_id: UUID,
        name: str | None = None,
        description: str | None = None,
        objective: str | None = None,
    ) -> Project:
        """Update a project's descriptive fields.

        Args:
            project_id: The UUID of the project.
            name: Optional new project name.
            description: Optional new project description.
            objective: Optional new project objective.

        Returns:
            The updated Project domain model.
        """
        project = self._get_active_project(project_id)

        modified = False
        if name is not None:
            if not name.strip():
                raise ProjectException("Project name cannot be empty.")
            project.name = name.strip()
            modified = True

        if description is not None:
            project.description = description.strip()
            modified = True

        if objective is not None:
            project.objective = objective.strip()
            modified = True

        if modified:
            project.updated_at = datetime.now(UTC)
            self.repository.save(project)

        return project

    def update_status(self, project_id: UUID, status: ProjectStatus) -> Project:
        """Update the project's operational state.

        Args:
            project_id: The UUID of the project.
            status: The new ProjectStatus to transition to.

        Returns:
            The updated Project domain model.
        """
        project = self._get_active_project(project_id)

        if project.status != status:
            project.status = status
            project.updated_at = datetime.now(UTC)
            self.repository.save(project)

        return project
