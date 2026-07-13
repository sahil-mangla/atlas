"""Serialization logic for the Architecture domain."""

from typing import Any

from engine.domain.architecture import Architecture


def serialize_architecture(architecture: Architecture) -> dict[str, Any]:
    """Convert Architecture aggregate into a dictionary."""
    return architecture.model_dump(mode="json")


def deserialize_architecture(data: dict[str, Any]) -> Architecture:
    """Reconstruct Architecture aggregate from a dictionary."""
    return Architecture.model_validate(data)
