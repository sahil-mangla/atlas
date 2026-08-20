"""Ambient, request-scoped capture of AI provider usage.

``atlas`` (the request/envelope boundary) and ``engine.ai`` (the provider-call
boundary) sit at different call-stack depths, and the codebase enforces
strict one-directional layering (``atlas -> engine -> shared``): ``engine``
never imports ``atlas``. A contextvar living here -- the one layer both sides
can import -- lets ``engine.ai.executor.PromptExecutor`` report token usage
without any signature change to the capability/orchestration chain in
between, and without ``engine`` reaching into ``atlas``.

``record_usage`` is a safe no-op when no capture is active, so code that
constructs ``PromptExecutor`` directly (outside ``Atlas.handle()``) is
unaffected.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AIUsageRecord:
    """One provider call's token usage, captured during a request."""

    provider: str
    prompt_tokens: int
    completion_tokens: int


@dataclass
class _UsageCapture:
    calls: list[AIUsageRecord] = field(default_factory=list)


_current: ContextVar[_UsageCapture | None] = ContextVar("_current", default=None)


def start_capture() -> Token[_UsageCapture | None]:
    """Begin capturing AI usage for the current request. Returns a reset token."""
    return _current.set(_UsageCapture())


def record_usage(provider: str, prompt_tokens: int, completion_tokens: int) -> None:
    """Record one provider call's usage against the active capture, if any."""
    capture = _current.get()
    if capture is not None:
        capture.calls.append(AIUsageRecord(provider, prompt_tokens, completion_tokens))


def finish_capture(token: Token[_UsageCapture | None]) -> tuple[AIUsageRecord, ...]:
    """End the capture started by ``start_capture`` and return what it collected."""
    capture = _current.get()
    _current.reset(token)
    return tuple(capture.calls) if capture is not None else ()
