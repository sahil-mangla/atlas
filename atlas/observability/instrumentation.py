"""Wires the envelope-boundary and provider-boundary observability hooks together."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from atlas.capabilities.base import CapabilityName
from atlas.commands import Command
from atlas.contracts.envelope import RequestEnvelope, ResponseEnvelope
from atlas.observability.exporter import TraceExporter
from atlas.observability.models import TraceOutcome, TraceRecord
from shared.observability.usage_context import (
    AIUsageRecord,
    finish_capture,
    start_capture,
)

logger = logging.getLogger(__name__)


def instrument_request(
    envelope: RequestEnvelope[Any],
    dispatch: Callable[[RequestEnvelope[Any]], ResponseEnvelope[Any]],
    capability_lookup: Callable[[type[Command]], CapabilityName | None],
    exporter: TraceExporter,
) -> ResponseEnvelope[Any]:
    """Dispatch ``envelope`` through ``dispatch``, exporting a ``TraceRecord`` for it.

    If ``dispatch`` raises anything other than the ``ApplicationError`` it
    already catches internally, that exception propagates unchanged after an
    error trace is exported. An exporter failure is caught and logged, never
    allowed to break the actual response or replace the original exception:
    an observability feature must not be able to take down request handling.
    """
    received_at = datetime.now(UTC)
    start = time.perf_counter()
    token = start_capture()
    dispatch_error: Exception | None = None
    try:
        response = dispatch(envelope)
    except Exception as error:
        dispatch_error = error
    finally:
        usage_calls = finish_capture(token)
    latency_ms = (time.perf_counter() - start) * 1000

    if dispatch_error is not None:
        _export_trace(
            exporter,
            _build_trace_record(
                envelope=envelope,
                response=None,
                capability=capability_lookup(type(envelope.command)),
                usage_calls=usage_calls,
                latency_ms=latency_ms,
                timestamp=received_at,
            ),
        )
        raise dispatch_error

    record = _build_trace_record(
        envelope=envelope,
        response=response,
        capability=capability_lookup(type(envelope.command)),
        usage_calls=usage_calls,
        latency_ms=latency_ms,
        timestamp=received_at,
    )
    _export_trace(exporter, record)
    return response


def _export_trace(exporter: TraceExporter, record: TraceRecord) -> None:
    try:
        exporter.export(record)
    except Exception:
        logger.warning(
            "Failed to export trace record for request_id=%s",
            record.request_id,
            exc_info=True,
        )


def _build_trace_record(  # noqa: PLR0913
    envelope: RequestEnvelope[Any],
    response: ResponseEnvelope[Any] | None,
    capability: CapabilityName | None,
    usage_calls: tuple[AIUsageRecord, ...],
    latency_ms: float,
    timestamp: datetime,
) -> TraceRecord:
    ai_provider: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    if usage_calls:
        ai_provider = usage_calls[0].provider
        prompt_tokens = sum(call.prompt_tokens for call in usage_calls)
        completion_tokens = sum(call.completion_tokens for call in usage_calls)
        total_tokens = prompt_tokens + completion_tokens

    outcome = (
        TraceOutcome.ERROR
        if response is None or response.error is not None
        else TraceOutcome.SUCCESS
    )
    return TraceRecord(
        request_id=envelope.request_id,
        timestamp=timestamp,
        adapter=envelope.adapter.kind,
        capability=capability,
        ai_provider=ai_provider,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        outcome=outcome,
        error_code=(
            response.error.code
            if response is not None and response.error is not None
            else None
        ),
    )
