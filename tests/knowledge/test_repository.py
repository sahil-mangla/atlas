from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from engine.domain.enums import (
    KnowledgeActorType,
    KnowledgeCandidateStatus,
    KnowledgeCategory,
    KnowledgeSourceType,
    PublishedKnowledgeStatus,
)
from engine.domain.knowledge import (
    KnowledgeActor,
    KnowledgeCandidate,
    KnowledgePersistenceDocument,
    KnowledgeProvenance,
    PublishedKnowledge,
)
from engine.knowledge.exceptions import InvalidKnowledgeException
from engine.knowledge.fs_repository import FilesystemKnowledgeRepository
from engine.knowledge.repository import KnowledgeRepository


class MockKnowledgeRepo(KnowledgeRepository):
    def __init__(self) -> None:
        self.documents: dict[str, KnowledgePersistenceDocument] = {}

    def load_document(self, project_id: UUID) -> KnowledgePersistenceDocument | None:
        return self.documents.get(str(project_id))

    def save_document(self, document: KnowledgePersistenceDocument) -> None:
        self.documents[str(document.project_id)] = document

    def delete_all(self, project_id: UUID) -> None:
        self.documents.pop(str(project_id), None)


def test_knowledge_repository_mock() -> None:
    repo = MockKnowledgeRepo()
    project_id = uuid4()
    candidate = KnowledgeCandidate(
        id=uuid4(),
        project_id=project_id,
        title="Test",
        content="Test content",
        category=KnowledgeCategory.LESSON_LEARNED,
        rationale="Because",
        provenance=KnowledgeProvenance(
            source_type=KnowledgeSourceType.RESEARCH_SNAPSHOT,
            source_id=uuid4(),
            extracted_at=datetime.now(UTC),
            actor=KnowledgeActor(
                actor_type=KnowledgeActorType.SYSTEM,
                actor_id="sys",
                display_name="System",
            ),
        ),
        author=KnowledgeActor(
            actor_type=KnowledgeActorType.SYSTEM,
            actor_id="sys",
            display_name="System",
        ),
        created_at=datetime.now(UTC),
    )
    repo.save_candidate(candidate)

    assert len(repo.list_candidates(project_id)) == 1
    fetched = repo.get_candidate(project_id, candidate.id)
    assert fetched is not None
    assert fetched.title == "Test"

    repo.delete_all(project_id)
    assert len(repo.list_candidates(project_id)) == 0


def test_filesystem_knowledge_repository_lifecycle(tmp_path: Path) -> None:
    # 1. Initialize repo with a mock project repo returning tmp_path
    project_repo = Mock()
    project_repo.get_project_path.return_value = tmp_path
    repo = FilesystemKnowledgeRepository(project_repo)

    project_id = uuid4()

    # 2. Missing file behavior: should return None
    assert repo.load_document(project_id) is None

    # 3. Save candidate
    actor = KnowledgeActor(actor_type=KnowledgeActorType.HUMAN, actor_id="user1")
    candidate = KnowledgeCandidate(
        id=uuid4(),
        project_id=project_id,
        title="FS Test Candidate",
        content="Content for fs",
        category=KnowledgeCategory.STANDARD,
        rationale="Just a test",
        provenance=KnowledgeProvenance(
            source_type=KnowledgeSourceType.HUMAN_SUBMISSION,
            source_id=uuid4(),
            extracted_at=datetime.now(UTC),
            actor=actor
        ),
        author=actor,
        status=KnowledgeCandidateStatus.PENDING_REVIEW,
        created_at=datetime.now(UTC)
    )

    repo.save_candidate(candidate)

    # Check physical file exists at .atlas/knowledge.json
    expected_path = tmp_path / ".atlas" / "knowledge.json"
    assert expected_path.is_file()

    # 4. Load candidate and verify round-trip
    loaded_doc = repo.load_document(project_id)
    assert loaded_doc is not None
    assert len(loaded_doc.candidates) == 1
    assert loaded_doc.candidates[0].id == candidate.id
    assert loaded_doc.candidates[0].title == "FS Test Candidate"

    # Verify entity-centric getters
    fetched_candidate = repo.get_candidate(project_id, candidate.id)
    assert fetched_candidate is not None
    assert fetched_candidate.title == "FS Test Candidate"

    # 5. Overwrite behavior (save a modified version)
    candidate.title = "FS Test Candidate - Updated"
    repo.save_candidate(candidate)

    fetched_updated = repo.get_candidate(project_id, candidate.id)
    assert fetched_updated is not None
    assert fetched_updated.title == "FS Test Candidate - Updated"

    # 6. Save PublishedKnowledge
    published = PublishedKnowledge(
        id=uuid4(),
        project_id=project_id,
        title="Published Standard",
        content="Must use tests.",
        category=KnowledgeCategory.STANDARD,
        status=PublishedKnowledgeStatus.ACTIVE,
        provenance=candidate.provenance,
        author=actor,
        published_at=datetime.now(UTC),
        version=1,
        candidate_id=candidate.id,
        deduplication_fingerprint="fp1"
    )

    repo.save_published(published)

    fetched_pub = repo.get_published(project_id, published.id)
    assert fetched_pub is not None
    assert fetched_pub.title == "Published Standard"

    # 7. Immutability violation check (attempt to modify published content)
    # Creating a copy of the published object with modified content
    modified_published = PublishedKnowledge(
        id=published.id,
        project_id=published.project_id,
        title="Published Standard",
        content="Must use tests and mocks.",  # Mutated content
        category=published.category,
        status=published.status,
        provenance=published.provenance,
        author=published.author,
        published_at=published.published_at,
        version=published.version,
        candidate_id=published.candidate_id,
        deduplication_fingerprint=published.deduplication_fingerprint
    )

    with pytest.raises(ValueError, match="Published knowledge content is immutable"):
        repo.save_published(modified_published)

    # 8. Corrupted JSON file handling
    expected_path.write_text("invalid json content", encoding="utf-8")
    with pytest.raises(InvalidKnowledgeException, match="Failed to parse knowledge data"):
        repo.load_document(project_id)

    # 9. Clean deletion
    repo.delete_all(project_id)
    assert not expected_path.exists()
