"""Tests for the TraceRecord/TraceOutcome schema."""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from atlas.adapters.protocol import AdapterKind
from atlas.capabilities.base import CapabilityName
from atlas.contracts.errors import PlatformErrorCode
from atlas.observability.models import TraceOutcome, TraceRecord


def _record(**overrides: object) -> TraceRecord:
    defaults: dict[str, object] = {
        "request_id": uuid4(),
        "timestamp": datetime.now(UTC),
        "adapter": AdapterKind.AI,
        "capability": CapabilityName.PROJECT,
        "latency_ms": 12.5,
        "outcome": TraceOutcome.SUCCESS,
    }
    defaults.update(overrides)
    return TraceRecord(**defaults)  # type: ignore[arg-type]


def test_record_constructs_with_only_required_fields() -> None:
    record = _record()
    assert record.ai_provider is None
    assert record.prompt_tokens is None
    assert record.completion_tokens is None
    assert record.total_tokens is None
    assert record.cost_usd is None
    assert record.error_code is None


def test_record_round_trips_through_json() -> None:
    record = _record(
        ai_provider="gemini",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )

    parsed = TraceRecord.model_validate(json.loads(record.model_dump_json()))

    assert parsed == record


def test_error_record_carries_error_code() -> None:
    record = _record(
        capability=None,
        outcome=TraceOutcome.ERROR,
        error_code=PlatformErrorCode.PROJECT_NOT_FOUND,
    )
    assert record.outcome == TraceOutcome.ERROR
    assert record.error_code == PlatformErrorCode.PROJECT_NOT_FOUND
    assert record.capability is None


def test_record_is_frozen() -> None:
    record = _record()
    with pytest.raises(ValidationError):
        record.latency_ms = 1.0
