"""Tests for the EngineeringReview model."""

import pytest
from pydantic import ValidationError

from engine.domain.review import EngineeringReview


def test_engineering_review_creation() -> None:
    review = EngineeringReview()

    assert review.completed == []
    assert review.blocking_issues == []
    assert review.optional_improvements == []
    assert review.confidence == 0.0
    assert review.approved is False

    # Test explicit values
    review_custom = EngineeringReview(
        completed=["Task 1"],
        blocking_issues=["Error"],
        optional_improvements=["Refactor"],
        confidence=0.8,
        approved=True,
    )

    assert review_custom.completed == ["Task 1"]
    assert review_custom.blocking_issues == ["Error"]
    assert review_custom.optional_improvements == ["Refactor"]
    assert review_custom.confidence == 0.8
    assert review_custom.approved is True


def test_engineering_review_validation() -> None:
    with pytest.raises(ValidationError):
        # Confidence must be <= 1.0
        EngineeringReview(confidence=1.5)

    with pytest.raises(ValidationError):
        # Confidence must be >= 0.0
        EngineeringReview(confidence=-0.5)
