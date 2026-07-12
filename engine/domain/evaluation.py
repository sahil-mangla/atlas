"""Evaluation domain models for the ATLAS platform.

Evaluation models the outcomes of quality checks, requirements verification,
and code compliance audits conducted against the Architecture and
Engineering Specifications.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from engine.domain.enums import EvaluationStatus, FindingSeverity


class ReviewFinding(BaseModel):
    """A single audit observation produced during an evaluation pass."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique finding identifier.",
    )
    description: str = Field(
        description="What was observed during the review.",
    )
    severity: FindingSeverity = Field(
        description="Impact classification of this finding.",
    )
    location: str = Field(
        default="",
        description=(
            "File path, component name, or code reference where the finding applies."
        ),
    )


class RequirementCoverage(BaseModel):
    """Tracks whether a specific requirement has been implemented and verified."""

    requirement_id: str = Field(
        description="Unique identifier of the requirement being tracked.",
    )
    description: str = Field(
        description="Human-readable description of the requirement.",
    )
    covered: bool = Field(
        default=False,
        description=(
            "Whether this requirement has been addressed in the implementation."
        ),
    )
    notes: str = Field(
        default="",
        description=(
            "Additional context about coverage status or verification approach."
        ),
    )


class Evaluation(BaseModel):
    """The formal quality assessment of implemented changes.

    Evaluation records whether the implemented code meets the requirements
    defined in Engineering Specifications and aligns with the Architecture.
    It is the authoritative record of a review pass outcome.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique evaluation identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    specification_id: UUID | None = Field(
        default=None,
        description="Reference to the EngineeringSpecification being evaluated.",
    )
    status: EvaluationStatus = Field(
        default=EvaluationStatus.PENDING,
        description="Current outcome state of this evaluation.",
    )
    quality_summary: str = Field(
        default="",
        description=(
            "Cohesion scores, compliance ratings, and structural metrics summary."
        ),
    )
    requirement_coverage: list[RequirementCoverage] = Field(
        default_factory=list,
        description="Checklist mapping implementation items back to requirements.",
    )
    findings: list[ReviewFinding] = Field(
        default_factory=list,
        description=(
            "Passed checks, warnings, and blocking defects discovered during review."
        ),
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actions recommended to resolve warnings or blocking defects.",
    )
    evaluated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the evaluation was completed.",
    )
