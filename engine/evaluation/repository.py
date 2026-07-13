"""Abstract repository interface for the Evaluation aggregate."""

from abc import ABC, abstractmethod
from uuid import UUID

from engine.domain.evaluation import Evaluation


class EvaluationRepository(ABC):
    """Abstract interface governing the persistence of Evaluation aggregates."""

    @abstractmethod
    def save(self, evaluation: Evaluation) -> None:
        """Persist the Evaluation aggregate root.

        Args:
            evaluation: The Evaluation aggregate root to save.
        """
        pass

    @abstractmethod
    def get_by_project_id(self, project_id: UUID) -> Evaluation | None:
        """Retrieve the Evaluation aggregate root for a given project ID.

        Args:
            project_id: The UUID of the project.

        Returns:
            The Evaluation aggregate if found, otherwise None.
        """
        pass

    @abstractmethod
    def exists(self, project_id: UUID) -> bool:
        """Check whether an Evaluation context exists for a given project ID.

        Args:
            project_id: The UUID of the project.

        Returns:
            True if the evaluation exists, otherwise False.
        """
        pass
