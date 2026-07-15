"""Traceability models for tracking engineering provenance across ATLAS."""

from uuid import UUID

from pydantic import BaseModel, Field


class TraceabilityLink(BaseModel):
    """A lightweight reference connecting an artifact to its upstream justification.

    Existence validation of the target UUID is delegated to the ArtifactValidationService,
    keeping the domain layer decoupled from global state checks.
    """

    source_id: UUID = Field(
        description="The ID of the originating concept (e.g. Evidence, Finding, Epic)."
    )
    description: str = Field(
        default="", description="Optional description of the relationship."
    )
