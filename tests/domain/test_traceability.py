"""Tests for the TraceabilityLink model."""

from uuid import uuid4

from engine.domain.traceability import TraceabilityLink


def test_traceability_link_creation() -> None:
    source_id = uuid4()
    link = TraceabilityLink(
        source_id=source_id, description="Based on research finding."
    )

    assert link.source_id == source_id
    assert link.description == "Based on research finding."

    # Test default description
    link_no_desc = TraceabilityLink(source_id=source_id)
    assert link_no_desc.description == ""
