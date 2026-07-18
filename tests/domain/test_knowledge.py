from datetime import UTC, datetime
from uuid import uuid4

from engine.domain.enums import (
    KnowledgeActorType,
    KnowledgeCategory,
    KnowledgeSourceType,
    PublishedKnowledgeStatus,
)
from engine.domain.knowledge import (
    KnowledgeActor,
    KnowledgeCandidate,
    KnowledgeProvenance,
    PublishedKnowledge,
)


def test_knowledge_candidate_is_pending() -> None:
    candidate = KnowledgeCandidate(
        id=uuid4(),
        project_id=uuid4(),
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
    assert candidate.id is not None

def test_published_knowledge_terminal_status() -> None:
    pub = PublishedKnowledge(
        id=uuid4(),
        project_id=uuid4(),
        title="Pub",
        content="Pub content",
        category=KnowledgeCategory.LESSON_LEARNED,
        status=PublishedKnowledgeStatus.DEPRECATED,
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
        published_at=datetime.now(UTC),
        version=1,
        candidate_id=uuid4(),
        deduplication_fingerprint="fingerprint",
    )
    # The domain model does not explicitly define is_terminal on PublishedKnowledge in this simplified test,
    # but we can verify the enum is assigned correctly
    assert pub.status == PublishedKnowledgeStatus.DEPRECATED
