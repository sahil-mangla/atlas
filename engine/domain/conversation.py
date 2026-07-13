"""Conversation and ephemeral chat domain models."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import ConversationRole


class ConversationMessage(BaseModel):
    """An individual message in an ephemeral conversation."""

    id: UUID = Field(default_factory=uuid4, description="Unique message ID.")
    role: ConversationRole = Field(description="Role of the sender.")
    content: str = Field(description="Text content of the message.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the message was created.",
    )


class ConversationSession(BaseModel):
    """Aggregate root for an isolated chat context."""

    id: UUID = Field(default_factory=uuid4, description="Unique session ID.")
    project_id: UUID = Field(description="The project this session belongs to.")
    title: str = Field(default="New Conversation", description="Session title.")
    messages: list[ConversationMessage] = Field(
        default_factory=list, description="Ordered list of messages."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Session creation timestamp.",
    )


class MemoryCandidate(BaseModel):
    """A formal recommendation by the AI to persist information into Engineering Memory."""

    id: UUID = Field(default_factory=uuid4, description="Candidate ID.")
    project_id: UUID = Field(description="The project this candidate targets.")
    content: str = Field(description="The core knowledge recommended for persistence.")
    rationale: str = Field(description="Why the AI believes this should be remembered.")
    source_conversation_id: UUID | None = Field(
        default=None, description="The session that triggered this recommendation."
    )
