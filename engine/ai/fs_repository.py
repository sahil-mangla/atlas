"""Filesystem implementation of the Conversation repository."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from engine.ai.exceptions import InvalidConversationException
from engine.ai.repository import ConversationRepository, ProposalRepository
from engine.ai.serializers import deserialize_conversation, serialize_conversation
from engine.domain.ai import AIProposal
from engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    EvaluationProposalDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
from engine.domain.conversation import ConversationSession
from engine.domain.enums import ProposalType
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
            raise InvalidConversationException(
                f"Failed to write conversation: {e}"
            ) from e

    def get_by_id(
        self, session_id: UUID, project_id: UUID | None = None
    ) -> ConversationSession | None:
        """Retrieve a ConversationSession by ID.

        When the caller has project context, pass ``project_id`` to avoid a
        workspace-wide scan. The context-free form remains for compatibility.
        """
        if project_id is not None:
            project = self.project_repo.get_by_id(project_id)
            projects = [project] if project else []
        else:
            projects = self.project_repo.discover()
        for project in projects:
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


class FilesystemProposalRepository(ProposalRepository):
    """Filesystem-backed durable storage for pending AI proposals."""

    def __init__(self, project_repo: ProjectRepository) -> None:
        self.project_repo = project_repo

    def _proposal_dir(self, project_id: UUID) -> Path:
        return self.project_repo.get_project_path(project_id) / ".atlas" / "proposals"

    def save(self, project_id: UUID, proposal: AIProposal[Any]) -> None:
        directory = self._proposal_dir(project_id)
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "project_id": str(project_id),
            "proposal": proposal.model_dump(mode="json"),
        }
        (directory / f"{proposal.id}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def get_by_id(self, proposal_id: UUID) -> tuple[UUID, AIProposal[Any]] | None:
        for project in self.project_repo.discover():
            file_path = self._proposal_dir(project.id) / f"{proposal_id}.json"
            if not file_path.is_file():
                continue
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            raw = payload["proposal"]
            draft_types: dict[ProposalType, type[BaseModel]] = {
                ProposalType.RESEARCH: ResearchProposalDraft,
                ProposalType.PLANNING: PlanningProposalDraft,
                ProposalType.ARCHITECTURE: ArchitectureProposalDraft,
                ProposalType.EVALUATION: EvaluationProposalDraft,
            }
            proposal_type = ProposalType(raw["proposal_type"])
            raw["data"] = draft_types[proposal_type].model_validate(raw["data"])
            return UUID(payload["project_id"]), AIProposal[Any].model_validate(raw)
        return None

    def delete(self, proposal_id: UUID) -> None:
        for project in self.project_repo.discover():
            file_path = self._proposal_dir(project.id) / f"{proposal_id}.json"
            if file_path.is_file():
                file_path.unlink()
                return
