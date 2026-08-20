"""Assertion logic: expected StepExpected vs. what a step actually produced."""

from __future__ import annotations

from typing import Any

from atlas.contracts.envelope import ResponseEnvelope
from atlas.observability.models import TraceRecord
from evals.schema import CheckSpec, Outcome, StepExpected
from evals.substitution import resolve_path, substitute


def score_step(
    expected: StepExpected,
    actual_outcome: Outcome,
    response: ResponseEnvelope[Any] | None,
    trace_record: TraceRecord | None,
    context: dict[str, Any],
) -> list[str]:
    """Return a list of failure reasons; empty means the step passed."""
    failures: list[str] = []

    if actual_outcome != expected.outcome:
        failures.append(
            f"outcome: expected {expected.outcome!r}, got {actual_outcome!r}"
        )
        # A wrong outcome makes every other assertion meaningless (e.g. no
        # response/trace_record exists at all for a validation_error).
        return failures

    if expected.is_asserted("capability"):
        actual_capability = (
            trace_record.capability.value
            if trace_record and trace_record.capability
            else None
        )
        if actual_capability != expected.capability:
            failures.append(
                f"capability: expected {expected.capability!r}, "
                f"got {actual_capability!r}"
            )

    if expected.is_asserted("ai_provider"):
        actual_provider = trace_record.ai_provider if trace_record else None
        if expected.ai_provider == "non_null":
            if actual_provider is None:
                failures.append("ai_provider: expected non-null, got null")
        elif actual_provider != expected.ai_provider:
            failures.append(
                f"ai_provider: expected {expected.ai_provider!r}, "
                f"got {actual_provider!r}"
            )

    if expected.is_asserted("error_code"):
        # Compared by enum member NAME (e.g. "PROJECT_NOT_FOUND"), not
        # `.value` (the wire-level lowercase string) -- task files write
        # the uppercase identifier, matching how the codebase itself
        # references PlatformErrorCode members.
        actual_code = response.error.code.name if response and response.error else None
        if actual_code != expected.error_code:
            failures.append(
                f"error_code: expected {expected.error_code!r}, got {actual_code!r}"
            )

    if expected.is_asserted("result_type"):
        actual_type = (
            type(response.result).__name__ if response and response.result else None
        )
        if actual_type != expected.result_type:
            failures.append(
                f"result_type: expected {expected.result_type!r}, got {actual_type!r}"
            )

    for check in expected.checks:
        failures.extend(_score_check(check, response, context))

    return failures


def _score_check(
    check: CheckSpec, response: ResponseEnvelope[Any] | None, context: dict[str, Any]
) -> list[str]:
    try:
        actual = resolve_path(response, check.field)
    except Exception as exc:
        return [f"check {check.field!r}: could not resolve path: {exc}"]

    if "equals" in check.model_fields_set:
        expected_value = substitute(check.equals, context)
        if _values_differ(actual, expected_value):
            return [
                f"check {check.field!r}: expected {expected_value!r}, got {actual!r}"
            ]
        return []

    if check.non_empty is not None:
        return _score_non_empty_check(check, actual)

    if check.type is not None:
        return _score_type_check(check, actual)

    return [f"check {check.field!r}: no assertion kind set"]


def _values_differ(actual: Any, expected: Any) -> bool:
    """Equality that doesn't care about list-vs-tuple.

    Some Result fields are typed ``tuple[str, ...]`` (e.g.
    ``CommitResult.blocking_issues``, ``KnowledgeCandidateResult.tags``)
    while others are plain ``list``; YAML has no tuple literal, so a task's
    ``equals: []`` always parses to a Python list. Comparing sequence
    contents rather than exact type keeps task authoring simple without
    task files needing to know which Result fields happen to be tuples.
    """
    if isinstance(actual, list | tuple) and isinstance(expected, list | tuple):
        return list(actual) != list(expected)
    return bool(actual != expected)


def _score_non_empty_check(check: CheckSpec, actual: Any) -> list[str]:
    is_empty = actual is None or (hasattr(actual, "__len__") and len(actual) == 0)
    if check.non_empty and is_empty:
        return [f"check {check.field!r}: expected non-empty, got {actual!r}"]
    return []


def _score_type_check(check: CheckSpec, actual: Any) -> list[str]:
    actual_type_name = type(actual).__name__
    if actual_type_name != check.type:
        return [
            f"check {check.field!r}: expected type {check.type!r}, "
            f"got {actual_type_name!r}"
        ]
    return []
