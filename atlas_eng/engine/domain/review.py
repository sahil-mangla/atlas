"""Review schema defining the canonical structure of engineering reviews."""

from pydantic import BaseModel, Field


class EngineeringReview(BaseModel):
    """The canonical schema for engineering reviews in ATLAS.

    This schema defines the language and structure of reviews.
    Execution behavior is handled by the Evaluation subsystem.
    """

    completed: list[str] = Field(
        default_factory=list,
        description="List of satisfied prerequisites and completed criteria.",
    )
    blocking_issues: list[str] = Field(
        default_factory=list,
        description="Critical defects or missing requirements preventing progression.",
    )
    optional_improvements: list[str] = Field(
        default_factory=list,
        description="Non-critical suggestions for future iteration.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Certainty score (0.0 to 1.0) of this review.",
    )
    approved: bool = Field(
        default=False,
        description="True if the review signifies approval to proceed.",
    )
