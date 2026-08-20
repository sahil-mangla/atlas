"""The trace record schema captured for every ``Atlas.handle()`` request."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from atlas.adapters.protocol import AdapterKind
from atlas.capabilities.base import CapabilityName
from atlas.contracts.errors import PlatformErrorCode


class TraceOutcome(StrEnum):
    """The result of a traced request.

    ``TIMEOUT`` is reserved but currently unproduced: no existing signal in
    ``engine.ai`` distinguishes a timeout from any other transport failure
    (both fold into the same ``AIProviderException``), so nothing sets this
    value yet. It is defined now so the schema doesn't need to change once
    that distinction exists.
    """

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class TraceRecord(BaseModel):
    """One request's worth of latency, capability, and AI-usage data."""

    model_config = ConfigDict(frozen=True)

    request_id: UUID
    timestamp: datetime
    adapter: AdapterKind
    capability: CapabilityName | None
    ai_provider: str | None = None
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None
    outcome: TraceOutcome
    error_code: PlatformErrorCode | None = None
