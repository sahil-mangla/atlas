"""Abstract repository interface for the Conversation aggregate."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from engine.domain.ai import AIProposal
from engine.domain.conversation import ConversationSession


class ConversationRepository(ABC):
    """Abstract interface governing persistence of ConversationSession aggregates."""

    @abstractmethod
    def save(self, session: ConversationSession) -> None:
        """Persist the ConversationSession aggregate root.

        Args:
            session: The ConversationSession aggregate root to save.
        """
        pass

    @abstractmethod
    def get_by_id(
        self, session_id: UUID, project_id: UUID | None = None
    ) -> ConversationSession | None:
        """Retrieve the ConversationSession aggregate root.

        Args:
            session_id: The UUID of the conversation session.

        Returns:
            The ConversationSession aggregate if found, otherwise None.
        """
        pass

    @abstractmethod
    def get_by_project_id(self, project_id: UUID) -> list[ConversationSession]:
        """Retrieve all ConversationSession aggregates for a given project.

        Args:
            project_id: The UUID of the project.

        Returns:
            A list of ConversationSession aggregates.
        """
        pass


class ProposalRepository(ABC):
    """Persistence boundary for generated AI proposals."""

    @abstractmethod
    def save(self, project_id: UUID, proposal: AIProposal[Any]) -> None:
        """Persist a proposal and its owning project."""
        pass

    @abstractmethod
    def get_by_id(self, proposal_id: UUID) -> tuple[UUID, AIProposal[Any]] | None:
        """Retrieve a proposal with its owning project."""
        pass

    @abstractmethod
    def delete(self, proposal_id: UUID) -> None:
        """Delete a completed proposal."""
        pass
