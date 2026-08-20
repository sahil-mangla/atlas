"""Variable capture/substitution and dotted-path resolution for task steps.

A step's captured values (plus the always-present ``request_id`` of the
step that just ran) form a "context" dict threaded to later steps. Command
field values of the form "$name" are replaced with a captured value before
constructing the Command; the same mechanism resolves "$name" inside a
check's `equals`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class UnknownCaptureReferenceError(Exception):
    pass


class InvalidPathError(Exception):
    pass


def substitute(value: Any, context: dict[str, Any]) -> Any:
    """Recursively replace "$name" string values using `context`."""
    if isinstance(value, str) and value.startswith("$"):
        name = value[1:]
        if name not in context:
            raise UnknownCaptureReferenceError(
                f"${name} was never captured (available: {sorted(context)})"
            )
        return context[name]
    if isinstance(value, dict):
        return {key: substitute(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute(item, context) for item in value]
    return value


def resolve_path(root: Any, path: str) -> Any:
    """Resolve a dotted path like "result.content.problem_statement" or
    "response.error.retryable" against `root` (a ResponseEnvelope).

    The first segment selects the root: "response" is the envelope itself,
    "result" is `response.result`. Remaining segments walk attribute access
    on pydantic models and key access on plain dicts (Result.content is a
    bare dict, so both are needed in the same path).
    """
    segments = path.split(".")
    head, *rest = segments
    if head == "response":
        current: Any = root
    elif head == "result":
        current = root.result
    else:
        raise InvalidPathError(f"Path must start with 'response.' or 'result.': {path}")

    for segment in rest:
        if isinstance(current, BaseModel):
            current = getattr(current, segment)
        elif isinstance(current, dict):
            current = current[segment]
        else:
            raise InvalidPathError(
                f"Cannot resolve segment {segment!r} of {path!r} on {current!r}"
            )
    return current
