"""Structural adapter contract for the ATLAS platform.

Any client (CLI, IDE, MCP, AI/agent, REST, Desktop) that wishes to be
considered platform-conformant satisfies ``PlatformAdapter`` structurally --
no adapter subclasses it. Conformance is verified via
``isinstance(adapter, PlatformAdapter)`` against the ``@runtime_checkable``
protocol, matching the project's existing preference for explicit
composition over inheritance hierarchies.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from atlas.capabilities.base import CapabilityName

if TYPE_CHECKING:
    from atlas._service import Atlas


class AdapterKind(StrEnum):
    """The kind of client presenting itself to the platform."""

    CLI = "cli"
    IDE = "ide"
    MCP = "mcp"
    AI = "ai"
    REST = "rest"
    DESKTOP = "desktop"


class AdapterContext(BaseModel):
    """Identity a client presents to the platform on every request."""

    model_config = ConfigDict(frozen=True)

    kind: AdapterKind
    name: str
    version: str


class PlatformCapabilityManifest(BaseModel):
    """What the platform tells an adapter it exposes, at the negotiated API version."""

    model_config = ConfigDict(frozen=True)

    api_version: str
    capabilities: tuple[CapabilityName, ...]


@runtime_checkable
class PlatformAdapter(Protocol):
    """Structural contract every client adapter satisfies.

    No adapter subclasses this -- conformance is structural (duck-typed).
    """

    @property
    def context(self) -> AdapterContext:
        """Return this adapter's identity."""
        ...

    def negotiate(self, atlas: Atlas) -> PlatformCapabilityManifest:
        """Return the capability manifest this adapter negotiates against."""
        ...
