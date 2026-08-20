"""Tests for the request-scoped AI usage capture contextvar."""

from shared.observability.usage_context import (
    finish_capture,
    record_usage,
    start_capture,
)


def test_record_usage_outside_a_capture_is_a_safe_noop() -> None:
    record_usage("gemini", prompt_tokens=10, completion_tokens=5)


def test_capture_collects_recorded_calls() -> None:
    token = start_capture()
    record_usage("gemini", prompt_tokens=10, completion_tokens=5)
    record_usage("anthropic", prompt_tokens=3, completion_tokens=1)

    calls = finish_capture(token)

    assert len(calls) == 2
    assert calls[0].provider == "gemini"
    assert calls[0].prompt_tokens == 10
    assert calls[0].completion_tokens == 5
    assert calls[1].provider == "anthropic"


def test_finish_capture_resets_so_a_later_capture_starts_empty() -> None:
    first_token = start_capture()
    record_usage("gemini", prompt_tokens=10, completion_tokens=5)
    finish_capture(first_token)

    second_token = start_capture()
    calls = finish_capture(second_token)

    assert calls == ()


def test_record_usage_after_finish_capture_is_a_safe_noop() -> None:
    token = start_capture()
    finish_capture(token)

    record_usage("gemini", prompt_tokens=10, completion_tokens=5)
