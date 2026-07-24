"""Filesystem implementation of the Planning repository.

S-03: Stores each project's Planning record as a dedicated JSON file inside
the project's own .atlas/ directory, consistent with the Memory and Workflow
repositories. This eliminates the prior workspace-wide multi-project flat file.

S-02: Missing files initialize empty state. Corrupt files raise
InvalidPlanningException rather than silently returning empty state.
"""

import json
from pathlib import Path
from uuid import UUID

from engine.domain.planning import Planning
from engine.planning.exceptions import (
    InvalidPlanningException,
    PlanningNotFoundException,
)
from engine.planning.repository import PlanningRepository
from engine.planning.serializers import deserialize_planning, serialize_planning
from engine.project.exceptions import ProjectNotFoundException
from engine.project.repository import ProjectRepository
from shared.atomic_write import atomic_write_text


class FilesystemPlanningRepository(PlanningRepository):
    """Filesystem-backed implementation of PlanningRepository.

    Stores each project's Planning aggregate as a JSON file at:
        <project_root>/.atlas/planning.json

    This is consistent with the per-project isolation used by the Memory
    and Workflow repositories.
    """

    def __init__(self, project_repo: ProjectRepository) -> None:
        """Initialize the repository.

        Args:
            project_repo: Abstract project repository used to resolve each
                project's root directory. Must implement get_project_path().
        """
        self.project_repo = project_repo

    def _planning_file(self, project_id: UUID) -> Path:
        """Resolve the .atlas/planning.json path for a project.

        Raises:
            ProjectNotFoundException: If the project has no registered path.
        """
        project_path: Path = self.project_repo.get_project_path(project_id)
        return project_path / ".atlas" / "planning.json"

    def save(self, planning: Planning) -> None:
        """Persist the Planning aggregate to the project's .atlas directory.

        Raises:
            PlanningNotFoundException: If the project is not registered.
            InvalidPlanningException: If writing to disk fails.
        """
        try:
            planning_file = self._planning_file(planning.project_id)
        except ProjectNotFoundException as e:
            raise PlanningNotFoundException(
                f"Project {planning.project_id} is not registered in the "
                "project repository and cannot store planning data."
            ) from e

        try:
            planning_file.parent.mkdir(parents=True, exist_ok=True)
            data = serialize_planning(planning)
            atomic_write_text(planning_file, json.dumps(data, indent=2))
        except OSError as e:
            raise InvalidPlanningException(
                f"Failed to write planning data to {planning_file}: {e}"
            ) from e

    def get_by_project_id(self, project_id: UUID) -> Planning | None:
        """Retrieve the Planning aggregate for a specific project.

        Returns:
            The Planning domain model if a planning file exists, otherwise None.

        Raises:
            InvalidPlanningException: If the planning file exists but is corrupt
                or cannot be read.
        """
        try:
            planning_file = self._planning_file(project_id)
        except ProjectNotFoundException:
            return None

        if not planning_file.is_file():
            return None

        try:
            with planning_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return deserialize_planning(data)
        except json.JSONDecodeError as e:
            raise InvalidPlanningException(
                f"Failed to read or parse planning from {planning_file}: {e}"
            ) from e
        except OSError as e:
            raise InvalidPlanningException(
                f"Failed to read planning file {planning_file}: {e}"
            ) from e

    def exists(self, project_id: UUID) -> bool:
        """Check whether a planning file exists for the given project."""
        try:
            return self._planning_file(project_id).is_file()
        except ProjectNotFoundException:
            return False

    def delete(self, project_id: UUID) -> None:
        """Remove an aggregate created by a failed unit of work."""
        try:
            self._planning_file(project_id).unlink(missing_ok=True)
        except OSError as e:
            raise InvalidPlanningException(
                f"Failed to remove planning data: {e}"
            ) from e
