"""Repository interface for the Research subsystem."""

from abc import ABC, abstractmethod
from uuid import UUID

from engine.domain.research import Research


class ResearchRepository(ABC):
    """Abstract interface for Research persistence."""

    @abstractmethod
    def save(self, research: Research) -> None:
        """Persist a Research aggregate to storage."""
        pass

    @abstractmethod
    def get_by_project_id(self, project_id: UUID) -> Research | None:
        """Retrieve Research by its owning project ID."""
        pass

    @abstractmethod
    def exists(self, project_id: UUID) -> bool:
        """Check if Research exists for a project."""
        pass
