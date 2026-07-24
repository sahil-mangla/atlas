"""Filesystem implementation of the MemoryRepository."""

import json
from uuid import UUID

from engine.domain.memory import Memory
from engine.memory.exceptions import InvalidMemoryException
from engine.memory.repository import MemoryRepository
from engine.memory.serializers import deserialize_memory, serialize_memory
from engine.project.exceptions import ProjectNotFoundException
from engine.project.repository import ProjectRepository
from shared.atomic_write import atomic_write_text


class FilesystemMemoryRepository(MemoryRepository):
    """Filesystem-backed implementation of MemoryRepository.

    Stores memory as JSON files within the project's .atlas/ directory.
    """

    def __init__(self, project_repo: ProjectRepository) -> None:
        self.project_repo = project_repo

    def save(self, memory: Memory) -> None:
        """Save the Memory aggregate to persistence."""
        # Use project repository to resolve physical path
        project_path = self.project_repo.get_project_path(memory.project_id)
        atlas_dir = project_path / ".atlas"
        memory_file = atlas_dir / "memory.json"

        try:
            atlas_dir.mkdir(parents=True, exist_ok=True)
            data = serialize_memory(memory)
            atomic_write_text(memory_file, json.dumps(data, indent=2))
        except OSError as e:
            raise InvalidMemoryException(
                f"Failed to write memory data to {memory_file}: {e}"
            ) from e

    def get_by_project_id(self, project_id: UUID) -> Memory | None:
        """Retrieve the memory aggregate for a specific project."""
        try:
            project_path = self.project_repo.get_project_path(project_id)
        except ProjectNotFoundException:
            # If the project path cannot be found, memory cannot be retrieved
            return None

        memory_file = project_path / ".atlas" / "memory.json"

        if not memory_file.is_file():
            return None

        try:
            with memory_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return deserialize_memory(data)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            raise InvalidMemoryException(
                f"Failed to read or parse memory from {memory_file}: {e}"
            ) from e

    def exists(self, project_id: UUID) -> bool:
        """Check if memory exists for a specific project."""
        try:
            project_path = self.project_repo.get_project_path(project_id)
            memory_file = project_path / ".atlas" / "memory.json"
            return memory_file.is_file()
        except ProjectNotFoundException:
            return False
