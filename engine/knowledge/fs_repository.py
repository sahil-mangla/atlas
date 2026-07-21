import json
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from engine.domain.knowledge import KnowledgePersistenceDocument
from engine.knowledge.exceptions import InvalidKnowledgeException
from engine.knowledge.repository import KnowledgeRepository
from engine.knowledge.serializers import (
    deserialize_knowledge_document,
    serialize_knowledge_document,
)
from engine.project.repository import ProjectRepository


class FilesystemKnowledgeRepository(KnowledgeRepository):
    def __init__(self, project_repo: ProjectRepository) -> None:
        self.project_repo = project_repo

    def _path(self, project_id: UUID) -> Path:
        return (
            self.project_repo.get_project_path(project_id) / ".atlas" / "knowledge.json"
        )

    def load_document(self, project_id: UUID) -> KnowledgePersistenceDocument | None:
        path = self._path(project_id)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return deserialize_knowledge_document(data)
        except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise InvalidKnowledgeException(
                f"Failed to parse knowledge data at {path}: {exc}"
            ) from exc

    def save_document(self, document: KnowledgePersistenceDocument) -> None:
        path = self._path(document.project_id)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(serialize_knowledge_document(document), indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise InvalidKnowledgeException(
                f"Failed to write knowledge data at {path}: {exc}"
            ) from exc

    def delete_all(self, project_id: UUID) -> None:
        path = self._path(project_id)
        if path.exists():
            path.unlink()
