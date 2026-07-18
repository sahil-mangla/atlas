"""Serialization logic for the Engineering Knowledge domain."""

from typing import Any

from engine.domain.knowledge import KnowledgePersistenceDocument


def serialize_knowledge_document(
    document: KnowledgePersistenceDocument,
) -> dict[str, Any]:
    """Convert the knowledge persistence envelope into JSON-compatible data."""
    return document.model_dump(mode="json")


def deserialize_knowledge_document(
    data: dict[str, Any],
) -> KnowledgePersistenceDocument:
    """Reconstruct the knowledge persistence envelope from JSON-compatible data."""
    return KnowledgePersistenceDocument.model_validate(data)
