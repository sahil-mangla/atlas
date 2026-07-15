"""Filesystem implementation of the Evaluation repository.

Stores each project's Evaluation record as a dedicated JSON file inside
the project's own .atlas/ directory.

Missing files initialize empty state. Corrupt files raise
InvalidEvaluationException rather than silently returning empty state.
"""

import json
from pathlib import Path
from uuid import UUID

from engine.domain.evaluation import Evaluation
from engine.evaluation.exceptions import (
    EvaluationNotFoundException,
    InvalidEvaluationException,
)
from engine.evaluation.repository import EvaluationRepository
from engine.evaluation.serializers import (
    deserialize_evaluation,
    serialize_evaluation,
)
from engine.project.exceptions import ProjectNotFoundException
from engine.project.repository import ProjectRepository


class FilesystemEvaluationRepository(EvaluationRepository):
    """Filesystem-backed implementation of EvaluationRepository.

    Stores each project's Evaluation aggregate as a JSON file at:
        <project_root>/.atlas/evaluation.json
    """

    def __init__(self, project_repo: ProjectRepository) -> None:
        """Initialize the repository.

        Args:
            project_repo: Abstract project repository used to resolve each
                project's root directory.
        """
        self.project_repo = project_repo

    def _evaluation_file(self, project_id: UUID) -> Path:
        """Resolve the .atlas/evaluation.json path for a project.

        Raises:
            ProjectNotFoundException: If the project has no registered path.
        """
        project_path: Path = self.project_repo.get_project_path(project_id)
        return project_path / ".atlas" / "evaluation.json"

    def save(self, evaluation: Evaluation) -> None:
        """Persist the Evaluation aggregate to the project's .atlas directory.

        Raises:
            EvaluationNotFoundException: If the project is not registered.
            InvalidEvaluationException: If writing to disk fails.
        """
        try:
            evaluation_file = self._evaluation_file(evaluation.project_id)
        except ProjectNotFoundException as e:
            raise EvaluationNotFoundException(
                f"Project {evaluation.project_id} is not registered in the "
                "project repository and cannot store evaluation data."
            ) from e

        try:
            evaluation_file.parent.mkdir(parents=True, exist_ok=True)
            data = serialize_evaluation(evaluation)
            with evaluation_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            raise InvalidEvaluationException(
                f"Failed to write evaluation data to {evaluation_file}: {e}"
            ) from e

    def get_by_project_id(self, project_id: UUID) -> Evaluation | None:
        """Retrieve the Evaluation aggregate for a specific project.

        Returns:
            The Evaluation domain model if an evaluation file exists, otherwise None.

        Raises:
            InvalidEvaluationException: If the file is corrupt or cannot be read.
        """
        try:
            evaluation_file = self._evaluation_file(project_id)
        except ProjectNotFoundException:
            return None

        if not evaluation_file.is_file():
            return None

        try:
            with evaluation_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return deserialize_evaluation(data)
        except json.JSONDecodeError as e:
            raise InvalidEvaluationException(
                f"Failed to read or parse evaluation from {evaluation_file}: {e}"
            ) from e
        except OSError as e:
            raise InvalidEvaluationException(
                f"Failed to read evaluation file {evaluation_file}: {e}"
            ) from e

    def exists(self, project_id: UUID) -> bool:
        """Check whether an evaluation file exists for the given project."""
        try:
            return self._evaluation_file(project_id).is_file()
        except ProjectNotFoundException:
            return False

    def delete(self, project_id: UUID) -> None:
        """Remove an aggregate created by a failed unit of work."""
        try:
            self._evaluation_file(project_id).unlink(missing_ok=True)
        except OSError as e:
            raise InvalidEvaluationException(
                f"Failed to remove evaluation data: {e}"
            ) from e
