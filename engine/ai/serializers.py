"""Serialization logic for the AI Integration domain."""

from typing import Any

from engine.domain.conversation import ConversationSession


def serialize_conversation(session: ConversationSession) -> dict[str, Any]:
    """Convert ConversationSession aggregate into a dictionary."""
    return session.model_dump(mode="json")


def deserialize_conversation(data: dict[str, Any]) -> ConversationSession:
    """Reconstruct ConversationSession aggregate from a dictionary."""
    return ConversationSession.model_validate(data)
