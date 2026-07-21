from datetime import UTC, datetime
from uuid import uuid4

from engine.domain.enums import (
    KnowledgeActorType,
    KnowledgeCategory,
    KnowledgeSourceType,
)
from engine.domain.knowledge import (
    KnowledgeActor,
    KnowledgePersistenceDocument,
    KnowledgeProvenance,
    PublishedKnowledge,
)
from engine.knowledge.serializers import (
    deserialize_knowledge_document,
    serialize_knowledge_document,
)


def test_knowledge_document_serializer_round_trip() -> None:
    project_id = uuid4()
    actor = KnowledgeActor(actor_type=KnowledgeActorType.SYSTEM, actor_id="system")
    published = PublishedKnowledge(
        id=uuid4(),
        project_id=project_id,
        title="Testing standard",
        content="Run the tests.",
        category=KnowledgeCategory.STANDARD,
        version=1,
        provenance=KnowledgeProvenance(
            source_type=KnowledgeSourceType.HUMAN_SUBMISSION,
            source_id=uuid4(),
            extracted_at=datetime.now(UTC),
            actor=actor,
        ),
        author=actor,
        published_at=datetime.now(UTC),
        candidate_id=uuid4(),
        deduplication_fingerprint="fingerprint",
    )
    document = KnowledgePersistenceDocument(
        project_id=project_id, published=[published]
    )

    serialized = serialize_knowledge_document(document)
    restored = deserialize_knowledge_document(serialized)

    assert serialized["project_id"] == str(project_id)
    assert restored == document
