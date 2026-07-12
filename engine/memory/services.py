"""Service layer for the ATLAS Memory System."""

from uuid import UUID

from engine.domain.enums import MemoryCategory
from engine.domain.memory import Memory, MemoryEntry
from engine.memory.exceptions import MemoryNotFoundException
from engine.memory.repository import MemoryRepository


class MemoryCaptureService:
    """Service to capture new knowledge, context, artifacts, and decisions."""

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def add_entry(self, project_id: UUID, entry: MemoryEntry) -> MemoryEntry:
        """Add a new memory entry for a project.

        If the memory aggregate does not exist, it is created.

        Args:
            project_id: The UUID of the project.
            entry: The new MemoryEntry to add.

        Returns:
            The added MemoryEntry.
        """
        memory = self.repository.get_by_project_id(project_id)
        if not memory:
            memory = Memory(project_id=project_id)

        memory.add_entry(entry)
        self.repository.save(memory)
        return entry


class MemoryVersioningService:
    """Service to handle the hybrid append-only versioning of memory entries."""

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def supersede_entry(
        self, project_id: UUID, old_entry_id: UUID, new_entry: MemoryEntry
    ) -> MemoryEntry:
        """Supersede an existing entry with a new version.

        Args:
            project_id: The UUID of the project.
            old_entry_id: The UUID of the entry to supersede.
            new_entry: The new MemoryEntry.

        Returns:
            The newly added MemoryEntry.
            
        Raises:
            MemoryNotFoundException: If the memory aggregate is not found.
            ValueError: If the old entry doesn't exist or is already superseded.
        """
        memory = self.repository.get_by_project_id(project_id)
        if not memory:
            raise MemoryNotFoundException(
                f"Memory for project {project_id} could not be found."
            )

        # The Memory aggregate root enforces the versioning invariants
        memory.version_entry(old_entry_id, new_entry)
        self.repository.save(memory)
        return new_entry


class MemoryRetrievalService:
    """Service to retrieve memory entries by status or history."""

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def get_active_entries(self, project_id: UUID) -> list[MemoryEntry]:
        """Retrieve all currently active memory entries for a project.

        Args:
            project_id: The UUID of the project.

        Returns:
            A list of active MemoryEntry instances.
            
        Raises:
            MemoryNotFoundException: If the memory aggregate is not found.
        """
        memory = self.repository.get_by_project_id(project_id)
        if not memory:
            raise MemoryNotFoundException(
                f"Memory for project {project_id} could not be found."
            )
        return memory.get_active_entries()

    def get_entry_history(
        self, project_id: UUID, active_entry_id: UUID
    ) -> list[MemoryEntry]:
        """Retrieve the historical chain for a specific active entry.
        
        Args:
            project_id: The UUID of the project.
            active_entry_id: The UUID of the current active entry.
            
        Returns:
            A list of MemoryEntry instances representing the history,
            ordered newest to oldest.
        """
        memory = self.repository.get_by_project_id(project_id)
        if not memory:
            raise MemoryNotFoundException(
                f"Memory for project {project_id} could not be found."
            )

        # Build history chain
        entry_map = {e.id: e for e in memory.entries}
        current_entry = entry_map.get(active_entry_id)
        if not current_entry:
            raise ValueError(f"Entry {active_entry_id} not found.")

        history = []
        while current_entry:
            history.append(current_entry)
            if current_entry.supersedes_id:
                current_entry = entry_map.get(current_entry.supersedes_id)
            else:
                current_entry = None

        return history


class MemoryOrganizationService:
    """Service to filter and organize memory entries by category or type."""

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def filter_active_by_category(
        self, project_id: UUID, category: MemoryCategory
    ) -> list[MemoryEntry]:
        """Retrieve active memory entries matching a specific category.

        Args:
            project_id: The UUID of the project.
            category: The MemoryCategory to filter by.

        Returns:
            A list of matching active MemoryEntry instances.
        """
        memory = self.repository.get_by_project_id(project_id)
        if not memory:
            raise MemoryNotFoundException(
                f"Memory for project {project_id} could not be found."
            )

        return [
            e for e in memory.get_active_entries()
            if e.category == category
        ]

    def filter_active_by_type(
        self, project_id: UUID, category: MemoryCategory, entry_type: str
    ) -> list[MemoryEntry]:
        """Retrieve active memory entries matching a specific category and type.

        Args:
            project_id: The UUID of the project.
            category: The MemoryCategory.
            entry_type: The specific type string (e.g., "Architecture Decision").

        Returns:
            A list of matching active MemoryEntry instances.
        """
        category_entries = self.filter_active_by_category(project_id, category)
        return [e for e in category_entries if e.type == entry_type]
