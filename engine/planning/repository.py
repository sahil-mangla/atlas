"""Repository interface for the Planning subsystem."""

from abc import ABC, abstractmethod
from uuid import UUID

from engine.domain.planning import Planning


class PlanningRepository(ABC):
    """Abstract interface for Planning persistence."""

    @abstractmethod
    def save(self, planning: Planning) -> None:
        """Persist a Planning aggregate to storage."""
        pass

    @abstractmethod
    def get_by_project_id(self, project_id: UUID) -> Planning | None:
        """Retrieve Planning by its owning project ID."""
        pass

    @abstractmethod
    def exists(self, project_id: UUID) -> bool:
        """Check if Planning exists for a project."""
        pass
