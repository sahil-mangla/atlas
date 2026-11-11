"""Langfuse sink for high-level TraceRecords."""

from __future__ import annotations

import logging

from langfuse import Langfuse
from langfuse.api.resources.commons.errors import UnauthorizedError

from atlas.observability.exporter import TraceExporter
from atlas.observability.models import TraceRecord

logger = logging.getLogger(__name__)


class LangfuseTraceExporter(TraceExporter):
    """Exports Atlas request-level TraceRecords to Langfuse as parent traces.

    This acts as a bridge between our domain-specific TraceRecord and the
    Langfuse tracing backend.
    """

    def __init__(self) -> None:
        self._langfuse = Langfuse()

        # Verify auth immediately so we can fail fast during bootstrap if keys are wrong
        try:
            self._langfuse.auth_check()
            logger.info("Successfully authenticated with Langfuse")
        except UnauthorizedError:
            logger.warning("Langfuse authentication failed. Check your API keys.")
        except Exception as e:
            logger.warning("Failed to initialize Langfuse client: %s", e)

    def export(self, record: TraceRecord) -> None:
        """Pushes a completed trace record to Langfuse."""
        try:
            # Check if there is an active Langfuse trace from decorators
            from langfuse.decorators import langfuse_context  # noqa: PLC0415

            active_trace_id = langfuse_context.get_current_trace_id()
            trace_id = active_trace_id if active_trace_id else str(record.request_id)

            # We map our TraceRecord fields onto Langfuse's trace schema
            self._langfuse.trace(
                id=trace_id,
                name=record.capability or "Unknown Capability",
                start_time=record.timestamp,
                metadata={
                    "adapter": record.adapter,
                    "ai_provider": record.ai_provider,
                    "latency_ms": record.latency_ms,
                    "outcome": record.outcome,
                    "error_code": record.error_code,
                },
                tags=["atlas-cli"],
            )
            self._langfuse.flush()
        except Exception as e:
            logger.warning("Failed to export trace to Langfuse: %s", e)
