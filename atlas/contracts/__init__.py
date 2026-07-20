"""Platform contract layer: versioned request/response envelopes and errors.

This sub-module is part of the public ATLAS SDK surface. Adapter authors
(MCP, REST, IDE, AI/agent clients) import from here to build requests
through ``Atlas.handle()`` and interpret its responses.
"""

from atlas.contracts.envelope import RequestEnvelope, ResponseEnvelope
from atlas.contracts.errors import ErrorEnvelope, PlatformErrorCode
from atlas.contracts.version import PLATFORM_API_VERSION, SCHEMA_VERSION, is_compatible

__all__ = [
    "PLATFORM_API_VERSION",
    "SCHEMA_VERSION",
    "ErrorEnvelope",
    "PlatformErrorCode",
    "RequestEnvelope",
    "ResponseEnvelope",
    "is_compatible",
]
