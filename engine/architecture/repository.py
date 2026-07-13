"""Abstract repository interface for the Architecture aggregate."""

from abc import ABC, abstractmethod
from uuid import UUID

from engine.domain.architecture import Architecture


class ArchitectureRepository(ABC):
    """Abstract interface governing the persistence of Architecture aggregates."""

    @abstractmethod
    def save(self, architecture: Architecture) -> None:
        """Persist the Architecture aggregate root.

        Args:
            architecture: The Architecture aggregate root to save.
        """
        pass

    @abstractmethod
    def get_by_project_id(self, project_id: UUID) -> Architecture | None:
        """Retrieve the Architecture aggregate root for a given project ID.

        Args:
            project_id: The UUID of the project.

        Returns:
            The Architecture aggregate if found, otherwise None.
        """
        pass

    @abstractmethod
    def exists(self, project_id: UUID) -> bool:
        """Check whether an Architecture context exists for a given project ID.

        Args:
            project_id: The UUID of the project.

        Returns:
            True if the architecture exists, otherwise False.
        """
        pass
