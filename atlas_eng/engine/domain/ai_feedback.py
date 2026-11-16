"""Structured human feedback for AI proposals."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProposalFeedback(BaseModel):
    """Structured value object capturing human review comments for a proposal."""

    proposal_id: UUID
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    author: str
    feedback: str
