"""Serialization logic for the Research domain."""

from typing import Any

from engine.domain.research import Research


def serialize_research(research: Research) -> dict[str, Any]:
    """Convert Research aggregate into a dictionary."""
    return research.model_dump(mode="json")


def deserialize_research(data: dict[str, Any]) -> Research:
    """Reconstruct Research aggregate from a dictionary."""
    return Research.model_validate(data)
