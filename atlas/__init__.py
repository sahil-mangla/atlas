"""ATLAS Application Platform Layer.

This package exposes the canonical public SDK of the ATLAS engineering platform.
Client adapters (CLI, Desktop, Web, MCP, REST) should import only from this package.
"""

from atlas._bootstrap import _create_platform
from atlas._service import Atlas
from atlas.exceptions import BootstrapError

__all__ = ["Atlas", "create"]


def create() -> Atlas:
    """Construct and return the fully configured Atlas platform.

    This is the only function clients call to obtain the platform instance.
    Bootstrap and internal wiring are not exposed.

    Returns:
        The Atlas application facade.
    """
    try:
        return _create_platform()
    except BootstrapError:
        raise
    except Exception as exc:
        raise BootstrapError("ATLAS platform initialization failed.") from exc
