"""Optional Langfuse tracing behind a no-op default.

Langfuse is an optional extra (``pip install "atlas-eng[langfuse]"``). Every
traced call site imports ``observe`` and the ``update_*`` helpers from here
instead of from ``langfuse`` directly, so that:

- ATLAS installs and runs without the ``langfuse`` package;
- with the package installed but no keys configured, nothing is imported or
  initialised and nothing is printed (Langfuse otherwise warns on every
  command that it has no public key);
- keys may live in the project's ``.env`` file, which pydantic-settings
  reads but never exports to the process environment the Langfuse SDK
  reads.

Whether tracing is active is decided on first use, not at import time,
because decorators are applied when modules are imported -- before any
``.env`` file has been located.
"""

import functools
import importlib.util
import logging
import os
from collections.abc import Callable
from typing import Any

from dotenv import dotenv_values, find_dotenv

logger = logging.getLogger(__name__)

_KEY_VARIABLES = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
_ALL_VARIABLES = (*_KEY_VARIABLES, "LANGFUSE_HOST")

_enabled: bool | None = None


def _load_keys_from_dotenv() -> None:
    """Export Langfuse settings from the nearest ``.env`` into the environment.

    Values already set in the environment win, matching how ATLAS's own
    settings treat the ``.env`` file.
    """
    path = find_dotenv(usecwd=True)
    if not path:
        return
    values = dotenv_values(path)
    for name in _ALL_VARIABLES:
        value = values.get(name)
        if value and not os.environ.get(name):
            os.environ[name] = value


def is_enabled() -> bool:
    """True when Langfuse keys are configured and the package is installed."""
    global _enabled  # noqa: PLW0603 - computed once per process
    if _enabled is None:
        _load_keys_from_dotenv()
        configured = all(os.environ.get(name) for name in _KEY_VARIABLES)
        installed = importlib.util.find_spec("langfuse") is not None
        if configured and not installed:
            logger.warning(
                "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set but the "
                "langfuse package is not installed, so traces are not sent to "
                "Langfuse. Install it with: pip install 'atlas-eng[langfuse]'"
            )
        _enabled = configured and installed
    return _enabled


def reset() -> None:
    """Forget the cached decision (tests change the environment between cases)."""
    global _enabled  # noqa: PLW0603
    _enabled = None


def _langfuse_context() -> Any:
    from langfuse.decorators import langfuse_context  # noqa: PLC0415

    return langfuse_context


def observe[F: Callable[..., Any]](**options: Any) -> Callable[[F], F]:
    """Trace the decorated function with Langfuse when tracing is enabled.

    Takes the same keyword options as ``langfuse.decorators.observe``. When
    tracing is disabled the function runs untouched, and keyword arguments
    meant only for Langfuse (``langfuse_*``) are dropped before the call.
    """

    def decorate(function: F) -> F:
        traced: Callable[..., Any] | None = None

        @functools.wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal traced
            if not is_enabled():
                plain_kwargs = {
                    key: value
                    for key, value in kwargs.items()
                    if not key.startswith("langfuse_")
                }
                return function(*args, **plain_kwargs)
            if traced is None:
                from langfuse.decorators import (  # noqa: PLC0415
                    observe as langfuse_observe,
                )

                traced = langfuse_observe(**options)(function)
            return traced(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorate


def update_current_observation(**fields: Any) -> None:
    """Attach fields to the active Langfuse observation, if tracing is on."""
    if is_enabled():
        _langfuse_context().update_current_observation(**fields)


def update_current_trace(**fields: Any) -> None:
    """Attach fields to the active Langfuse trace, if tracing is on."""
    if is_enabled():
        _langfuse_context().update_current_trace(**fields)


def get_current_trace_id() -> str | None:
    """The active Langfuse trace ID, or ``None`` when tracing is off."""
    if not is_enabled():
        return None
    trace_id: str | None = _langfuse_context().get_current_trace_id()
    return trace_id
