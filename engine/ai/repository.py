"""Abstract repository interface for the Conversation aggregate."""

from abc import ABC, abstractmethod
from uuid import UUID

from engine.domain.conversation import ConversationSession


class ConversationRepository(ABC):
    """Abstract interface governing the persistence of ConversationSession aggregates."""

    @abstractmethod
    def save(self, session: ConversationSession) -> None:
        """Persist the ConversationSession aggregate root.

        Args:
            session: The ConversationSession aggregate root to save.
        """
        pass

    @abstractmethod
    def get_by_id(self, session_id: UUID) -> ConversationSession | None:
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
