"""Filesystem implementation of the Conversation repository."""

import json
from pathlib import Path
from uuid import UUID

from engine.ai.exceptions import InvalidConversationException
from engine.ai.repository import ConversationRepository
from engine.ai.serializers import deserialize_conversation, serialize_conversation
from engine.domain.conversation import ConversationSession
from engine.project.exceptions import ProjectNotFoundException
from engine.project.repository import ProjectRepository


class FilesystemConversationRepository(ConversationRepository):
    """Filesystem-backed implementation of ConversationRepository.

    Stores each conversation session as a JSON file at:
        <project_root>/.atlas/conversations/<session_id>.json
    """

    def __init__(self, project_repo: ProjectRepository) -> None:
        """Initialize the repository.

        Args:
            project_repo: Abstract project repository used to resolve paths.
        """
        self.project_repo = project_repo

    def _conversations_dir(self, project_id: UUID) -> Path:
        """Resolve the conversations directory for a project."""
        project_path: Path = self.project_repo.get_project_path(project_id)
        return project_path / ".atlas" / "conversations"

    def save(self, session: ConversationSession) -> None:
        """Persist the ConversationSession to disk."""
        try:
            conv_dir = self._conversations_dir(session.project_id)
        except ProjectNotFoundException as e:
            raise InvalidConversationException(
                f"Cannot save conversation to nonexistent project: {e}"
            ) from e

        try:
            conv_dir.mkdir(parents=True, exist_ok=True)
            session_file = conv_dir / f"{session.id}.json"
            data = serialize_conversation(session)
            with session_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            raise InvalidConversationException(f"Failed to write conversation: {e}") from e

    def get_by_id(self, session_id: UUID) -> ConversationSession | None:
        """Retrieve a ConversationSession by ID.
        
        Note: This naive implementation would require checking all projects,
        or we must assume the caller already knows the project_id.
        Since we only have project_repo for path resolution, scanning all projects
        is necessary unless we change the interface.
        
        For Stage 11, we will scan all projects.
        """
        for project in self.project_repo.discover():
            try:
                conv_dir = self._conversations_dir(project.id)
                session_file = conv_dir / f"{session_id}.json"
                if session_file.is_file():
                    with session_file.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    return deserialize_conversation(data)
            except Exception:
                continue
        return None

    def get_by_project_id(self, project_id: UUID) -> list[ConversationSession]:
        """Retrieve all conversations for a specific project."""
        try:
            conv_dir = self._conversations_dir(project_id)
        except ProjectNotFoundException:
            return []

        if not conv_dir.is_dir():
            return []

        sessions = []
        for session_file in conv_dir.glob("*.json"):
            try:
                with session_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(deserialize_conversation(data))
            except Exception as e:
                raise InvalidConversationException(
                    f"Corrupt conversation file {session_file}: {e}"
                ) from e
        return sessions
