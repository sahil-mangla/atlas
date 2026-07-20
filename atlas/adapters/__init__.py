"""Platform adapter boundary: the structural contract client adapters satisfy.

This sub-module is part of the public ATLAS SDK surface. Any client (CLI,
IDE, MCP, AI/agent, REST, Desktop) imports from here to declare its
``AdapterContext`` and negotiate a ``PlatformCapabilityManifest``.
"""

from atlas.adapters.protocol import (
    AdapterContext,
    AdapterKind,
    PlatformAdapter,
    PlatformCapabilityManifest,
)

__all__ = [
    "AdapterContext",
    "AdapterKind",
    "PlatformAdapter",
    "PlatformCapabilityManifest",
]
