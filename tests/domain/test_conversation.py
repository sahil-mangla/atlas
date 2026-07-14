from uuid import UUID, uuid4

from engine.domain.conversation import (
    ConversationMessage,
    ConversationSession,
    MemoryCandidate,
)
from engine.domain.enums import ConversationRole


def test_conversation_message() -> None:
    msg = ConversationMessage(role=ConversationRole.USER, content="Hello")
    assert isinstance(msg.id, UUID)
    assert msg.role == ConversationRole.USER
    assert msg.content == "Hello"


def test_conversation_session() -> None:
    proj_id = uuid4()
    session = ConversationSession(project_id=proj_id, title="Chat 1")
    assert isinstance(session.id, UUID)
    assert session.project_id == proj_id
    assert session.title == "Chat 1"
    assert session.messages == []


def test_memory_candidate() -> None:
    proj_id = uuid4()
    candidate = MemoryCandidate(
        project_id=proj_id,
        content="Use Python 3.12",
        rationale="Client requirement",
    )
    assert isinstance(candidate.id, UUID)
    assert candidate.project_id == proj_id
    assert candidate.content == "Use Python 3.12"
