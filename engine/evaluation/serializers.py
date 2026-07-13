"""Serialization logic for the Evaluation domain."""

from typing import Any

from engine.domain.evaluation import Evaluation


def serialize_evaluation(evaluation: Evaluation) -> dict[str, Any]:
    """Convert Evaluation aggregate into a dictionary."""
    return evaluation.model_dump(mode="json")


def deserialize_evaluation(data: dict[str, Any]) -> Evaluation:
    """Reconstruct Evaluation aggregate from a dictionary."""
    return Evaluation.model_validate(data)
