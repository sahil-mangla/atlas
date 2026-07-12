"""Abstract repository interface for the ATLAS Memory System."""

from abc import ABC, abstractmethod
from uuid import UUID

from engine.domain.memory import Memory


class MemoryRepository(ABC):
    """Abstract persistence interface for project Memory.
    
    The Memory repository handles persisting the Memory aggregate root.
    Serialization details are left to concrete implementations.
    """

    @abstractmethod
    def save(self, memory: Memory) -> None:
        """Save the memory aggregate to persistence.
        
        Args:
            memory: The Memory aggregate to save.
        """

    @abstractmethod
    def get_by_project_id(self, project_id: UUID) -> Memory | None:
        """Retrieve the memory aggregate for a specific project.
        
        Args:
            project_id: The UUID of the project.
            
        Returns:
            The Memory aggregate, or None if it doesn't exist.
        """

    @abstractmethod
    def exists(self, project_id: UUID) -> bool:
        """Check if memory exists for a specific project.
        
        Args:
            project_id: The UUID of the project.
            
        Returns:
            True if memory exists, False otherwise.
        """
