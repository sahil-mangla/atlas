"""Abstract repository interface for the ATLAS Workflow System."""

from abc import ABC, abstractmethod
from uuid import UUID

from engine.domain.workflow import Workflow


class WorkflowRepository(ABC):
    """Abstract persistence interface for project Workflow state.

    The repository handles serializing and saving the Workflow state machine.
    """

    @abstractmethod
    def save(self, workflow: Workflow) -> None:
        """Save the workflow state to persistence.

        Args:
            workflow: The Workflow domain model to save.
        """

    @abstractmethod
    def get_by_project_id(self, project_id: UUID) -> Workflow | None:
        """Retrieve the workflow state for a specific project.

        Args:
            project_id: The UUID of the project.

        Returns:
            The Workflow domain model, or None if it doesn't exist.
        """

    @abstractmethod
    def exists(self, project_id: UUID) -> bool:
        """Check if workflow state exists for a specific project.

        Args:
            project_id: The UUID of the project.

        Returns:
            True if it exists, False otherwise.
        """
