"""Metadata models for engineering artifacts."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ArtifactStatus(StrEnum):
    """Lifecycle state of an engineering artifact."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class ArtifactMetadata(BaseModel):
    """Shared metadata composed within every canonical engineering artifact.
    
    Provides standardized identity, versioning, and provenance tracking
    without forcing deep inheritance hierarchies.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique artifact identifier.")
    version: int = Field(default=1, description="Sequential version number.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the artifact was created.",
    )
    created_by: str = Field(
        default="system", description="Originating context (human or agent ID)."
    )
    status: ArtifactStatus = Field(
        default=ArtifactStatus.DRAFT,
        description="Current lifecycle state of the artifact.",
    )
