"""Filesystem implementation of the Research repository.

S-03: Stores each project's Research record as a dedicated JSON file inside
the project's own .atlas/ directory, consistent with the Memory and Workflow
repositories. This eliminates the prior workspace-wide multi-project flat file.

S-02: Missing files initialize empty state. Corrupt files raise
InvalidResearchException rather than silently returning empty state.
"""

import json
from pathlib import Path
from uuid import UUID

from engine.domain.research import Research
from engine.project.exceptions import ProjectNotFoundException
from engine.project.repository import ProjectRepository
from engine.research.exceptions import (
    InvalidResearchException,
    ResearchNotFoundException,
)
from engine.research.repository import ResearchRepository
from engine.research.serializers import deserialize_research, serialize_research


class FilesystemResearchRepository(ResearchRepository):
    """Filesystem-backed implementation of ResearchRepository.

    Stores each project's Research aggregate as a JSON file at:
        <project_root>/.atlas/research.json

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

    def _research_file(self, project_id: UUID) -> Path:
        """Resolve the .atlas/research.json path for a project.

        Raises:
            ProjectNotFoundException: If the project has no registered path.
        """
        project_path: Path = self.project_repo.get_project_path(project_id)
        return project_path / ".atlas" / "research.json"

    def save(self, research: Research) -> None:
        """Persist the Research aggregate to the project's .atlas directory.

        Raises:
            ResearchNotFoundException: If the project is not registered.
            InvalidResearchException: If writing to disk fails.
        """
        try:
            research_file = self._research_file(research.project_id)
        except ProjectNotFoundException as e:
            raise ResearchNotFoundException(
                f"Project {research.project_id} is not registered in the "
                "project repository and cannot store research data."
            ) from e

        try:
            research_file.parent.mkdir(parents=True, exist_ok=True)
            data = serialize_research(research)
            with research_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            raise InvalidResearchException(
                f"Failed to write research data to {research_file}: {e}"
            ) from e

    def get_by_project_id(self, project_id: UUID) -> Research | None:
        """Retrieve the Research aggregate for a specific project.

        Returns:
            The Research domain model if a research file exists, otherwise None.

        Raises:
            InvalidResearchException: If the research file exists but is corrupt
                or cannot be read.
        """
        try:
            research_file = self._research_file(project_id)
        except ProjectNotFoundException:
            return None

        if not research_file.is_file():
            return None

        try:
            with research_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return deserialize_research(data)
        except json.JSONDecodeError as e:
            raise InvalidResearchException(
                f"Failed to read or parse research from {research_file}: {e}"
            ) from e
        except OSError as e:
            raise InvalidResearchException(
                f"Failed to read research file {research_file}: {e}"
            ) from e

    def exists(self, project_id: UUID) -> bool:
        """Check whether a research file exists for the given project."""
        try:
            return self._research_file(project_id).is_file()
        except ProjectNotFoundException:
            return False

    def delete(self, project_id: UUID) -> None:
        """Remove an aggregate created by a failed unit of work."""
        try:
            self._research_file(project_id).unlink(missing_ok=True)
        except OSError as e:
            raise InvalidResearchException(
                f"Failed to remove research data: {e}"
            ) from e
