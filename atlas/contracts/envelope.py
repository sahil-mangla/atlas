"""Versioned request/response envelopes for the ATLAS platform.

Wraps the existing ``Command``/``Result`` DTOs without changing their shape.
Out-of-process or protocol-driven clients (MCP, REST, IDE, AI agents) attach
adapter identity, a request id, and an API version so the platform boundary
can serialize, log, and trace requests uniformly.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas.adapters.protocol import AdapterContext
from atlas.commands import Command
from atlas.contracts.errors import ErrorEnvelope
from atlas.contracts.version import PLATFORM_API_VERSION
from atlas.results import Result


class RequestEnvelope[TCommand: Command](BaseModel):
    """Versioned, adapter-attributed wrapper around an existing Command DTO."""

    model_config = ConfigDict(frozen=True)

    api_version: str = PLATFORM_API_VERSION
    request_id: UUID = Field(default_factory=uuid4)
    adapter: AdapterContext
    command: TCommand


class ResponseEnvelope[TResult: Result](BaseModel):
    """Versioned wrapper around an existing Result DTO or an ErrorEnvelope.

    Exactly one of ``result`` / ``error`` is populated per response.
    """

    model_config = ConfigDict(frozen=True)

    api_version: str = PLATFORM_API_VERSION
    request_id: UUID
    result: TResult | None = None
    error: ErrorEnvelope | None = None

    @model_validator(mode="after")
    def _exactly_one_of_result_or_error(self) -> ResponseEnvelope[TResult]:
        if (self.result is None) == (self.error is None):
            raise ValueError(
                "ResponseEnvelope requires exactly one of `result` or `error`."
            )
        return self
