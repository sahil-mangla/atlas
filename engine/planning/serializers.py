"""Serialization logic for the Planning domain."""

from typing import Any

from engine.domain.planning import Planning


def serialize_planning(planning: Planning) -> dict[str, Any]:
    """Convert Planning aggregate into a dictionary."""
    return planning.model_dump(mode="json")


def deserialize_planning(data: dict[str, Any]) -> Planning:
    """Reconstruct Planning aggregate from a dictionary."""
    return Planning.model_validate(data)
