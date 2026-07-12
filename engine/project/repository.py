"""Repository abstraction for the ATLAS Project System."""

from abc import ABC, abstractmethod
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
