"""Repository abstraction for the ATLAS Project System."""

from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from engine.domain.project import Project


class ProjectRepository(ABC):
    """Abstract repository for persisting and retrieving Project aggregates.

    This interface separates the Project Services from the concrete storage
    technology, ensuring the services remain clean and database-independent.
    """

    @abstractmethod
    def save(self, project: Project) -> None:
        """Persist or update the given project domain model.

        Args:
            project: The Project domain model to save.
        """

    @abstractmethod
    def get_by_id(self, project_id: UUID) -> Project | None:
        """Retrieve a project by its unique identifier.

        Args:
            project_id: The UUID of the project.

        Returns:
            The Project domain model if found, otherwise None.
        """

    @abstractmethod
    def discover(self) -> list[Project]:
        """Discover and list all available projects in the repository.

        Returns:
            A list of all discovered Project domain models.
        """

    @abstractmethod
    def get_project_path(self, project_id: UUID) -> Path:
        """Return the canonical filesystem path for a project's root directory.

        This is the single authoritative mechanism for resolving project storage
        locations. Dependent repositories (Memory, Workflow, Research, Planning)
        use this method rather than coupling to a concrete implementation.

        Args:
            project_id: The UUID of the project to resolve.

        Returns:
            The absolute Path to the project's root directory.

        Raises:
            ProjectNotFoundException: If the project is not tracked by this
                repository.
        """

    @abstractmethod
    def delete(self, project_id: UUID) -> None:
        """Remove this repository's record of the project.

        Used to roll back a failed create (e.g. workflow initialization
        failed after the project was persisted). Only removes the metadata
        this repository owns -- never the project's directory tree, which
        may pre-exist and hold unrelated content when the project was
        created at a caller-supplied custom path.

        Args:
            project_id: The UUID of the project to remove. A no-op if the
                project isn't tracked.
        """
