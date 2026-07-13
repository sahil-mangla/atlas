"""Filesystem implementation of the Architecture repository.

Stores each project's Architecture record as a dedicated JSON file inside
the project's own .atlas/ directory.

Missing files initialize empty state. Corrupt files raise
InvalidArchitectureException rather than silently returning empty state.
"""

import json
from pathlib import Path
from uuid import UUID

from engine.architecture.exceptions import (
    InvalidArchitectureException,
    ArchitectureNotFoundException,
)
from engine.architecture.repository import ArchitectureRepository
from engine.architecture.serializers import (
    deserialize_architecture,
    serialize_architecture,
)
from engine.domain.architecture import Architecture
from engine.project.exceptions import ProjectNotFoundException
from engine.project.repository import ProjectRepository


class FilesystemArchitectureRepository(ArchitectureRepository):
    """Filesystem-backed implementation of ArchitectureRepository.

    Stores each project's Architecture aggregate as a JSON file at:
        <project_root>/.atlas/architecture.json
    """

    def __init__(self, project_repo: ProjectRepository) -> None:
        """Initialize the repository.

        Args:
            project_repo: Abstract project repository used to resolve each
                project's root directory.
        """
        self.project_repo = project_repo

    def _architecture_file(self, project_id: UUID) -> Path:
        """Resolve the .atlas/architecture.json path for a project.

        Raises:
            ProjectNotFoundException: If the project has no registered path.
        """
        project_path: Path = self.project_repo.get_project_path(project_id)
        return project_path / ".atlas" / "architecture.json"

    def save(self, architecture: Architecture) -> None:
        """Persist the Architecture aggregate to the project's .atlas directory.

        Raises:
            ArchitectureNotFoundException: If the project is not registered.
            InvalidArchitectureException: If writing to disk fails.
        """
        try:
            architecture_file = self._architecture_file(architecture.project_id)
        except ProjectNotFoundException as e:
            raise ArchitectureNotFoundException(
                f"Project {architecture.project_id} is not registered in the "
                "project repository and cannot store architecture data."
            ) from e

        try:
            architecture_file.parent.mkdir(parents=True, exist_ok=True)
            data = serialize_architecture(architecture)
            with architecture_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            raise InvalidArchitectureException(
                f"Failed to write architecture data to {architecture_file}: {e}"
            ) from e

    def get_by_project_id(self, project_id: UUID) -> Architecture | None:
        """Retrieve the Architecture aggregate for a specific project.

        Returns:
            The Architecture domain model if an architecture file exists, otherwise None.

        Raises:
            InvalidArchitectureException: If the file is corrupt or cannot be read.
        """
        try:
            architecture_file = self._architecture_file(project_id)
        except ProjectNotFoundException:
            return None

        if not architecture_file.is_file():
            return None

        try:
            with architecture_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return deserialize_architecture(data)
        except json.JSONDecodeError as e:
            raise InvalidArchitectureException(
                f"Failed to read or parse architecture from {architecture_file}: {e}"
            ) from e
        except OSError as e:
            raise InvalidArchitectureException(
                f"Failed to read architecture file {architecture_file}: {e}"
            ) from e

    def exists(self, project_id: UUID) -> bool:
        """Check whether an architecture file exists for the given project."""
        try:
            return self._architecture_file(project_id).is_file()
        except ProjectNotFoundException:
            return False
