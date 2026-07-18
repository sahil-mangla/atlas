from abc import ABC, abstractmethod
from uuid import UUID

from engine.domain.enums import KnowledgeCandidateStatus, PublishedKnowledgeStatus
from engine.domain.knowledge import (
    KnowledgeCandidate,
    KnowledgePersistenceDocument,
    PublishedKnowledge,
)


class KnowledgeRepository(ABC):
    @abstractmethod
    def load_document(self, project_id: UUID) -> KnowledgePersistenceDocument | None: ...
    @abstractmethod
    def save_document(self, document: KnowledgePersistenceDocument) -> None: ...
    @abstractmethod
    def delete_all(self, project_id: UUID) -> None: ...

    def save_candidate(self, candidate: KnowledgeCandidate) -> None:
        document = self.load_document(candidate.project_id) or KnowledgePersistenceDocument(project_id=candidate.project_id)
        document.candidates = [item for item in document.candidates if item.id != candidate.id] + [candidate]
        self.save_document(document)

    def get_candidate(self, project_id: UUID, candidate_id: UUID) -> KnowledgeCandidate | None:
        document = self.load_document(project_id)
        return next((item for item in (document.candidates if document else []) if item.id == candidate_id), None)

    def list_candidates(self, project_id: UUID, status: KnowledgeCandidateStatus | None = None) -> list[KnowledgeCandidate]:
        items = (self.load_document(project_id) or KnowledgePersistenceDocument(project_id=project_id)).candidates
        return [item for item in items if status is None or item.status == status]

    def save_published(self, entry: PublishedKnowledge) -> None:
        document = self.load_document(entry.project_id) or KnowledgePersistenceDocument(project_id=entry.project_id)
        current = next((item for item in document.published if item.id == entry.id), None)
        if current and (current.title, current.content, current.category, current.tags) != (entry.title, entry.content, entry.category, entry.tags):
            raise ValueError("Published knowledge content is immutable.")
        document.published = [item for item in document.published if item.id != entry.id] + [entry]
        self.save_document(document)

    def get_published(self, project_id: UUID, entry_id: UUID) -> PublishedKnowledge | None:
        document = self.load_document(project_id)
        return next((item for item in (document.published if document else []) if item.id == entry_id), None)

    def list_published(self, project_id: UUID, status: PublishedKnowledgeStatus | None = None) -> list[PublishedKnowledge]:
        items = (self.load_document(project_id) or KnowledgePersistenceDocument(project_id=project_id)).published
        return [item for item in items if status is None or item.status == status]
