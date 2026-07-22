"""Unit tests for the shared post_json HTTP helper."""

import json
import logging
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import pytest

from engine.ai.adapters._http import post_json
from engine.ai.exceptions import AIProviderException


def _fake_response(body: dict[str, object]) -> Mock:
    response = Mock()
    response.read.return_value = json.dumps(body).encode()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    return response


def test_post_json_logs_request_duration_on_success(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Regression test: users tuning ATLAS_AI_TIMEOUT_SECONDS need real
    per-request timing data (see Finding-012) instead of guessing -- every
    request must log how long it actually took."""
    with (
        patch(
            "engine.ai.adapters._http.urlopen",
            return_value=_fake_response({"ok": True}),
        ),
        caplog.at_level(logging.INFO, logger="engine.ai.adapters._http"),
    ):
        result = post_json("http://localhost:1234/v1/chat/completions", {}, {})

    assert result == {"ok": True}
    assert len(caplog.records) == 1
    assert "completed in" in caplog.records[0].message
    assert "http://localhost:1234/v1/chat/completions" in caplog.records[0].message


def test_post_json_logs_request_duration_on_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The duration must also be logged when the request fails (e.g. a
    timeout), since that is exactly the case a user is trying to diagnose."""
    with (
        patch(
            "engine.ai.adapters._http.urlopen",
            side_effect=TimeoutError("timed out"),
        ),
        caplog.at_level(logging.INFO, logger="engine.ai.adapters._http"),
        pytest.raises(AIProviderException),
    ):
        post_json("http://localhost:1234/v1/chat/completions", {}, {})

    assert len(caplog.records) == 1
    assert "failed after" in caplog.records[0].message


def test_post_json_bare_timeout_gives_actionable_message() -> None:
    """RC-006 regression: a timeout must explain what happened and suggest
    the fix (raise ATLAS_AI_TIMEOUT_SECONDS), not a generic transport error."""
    with (
        patch(
            "engine.ai.adapters._http.urlopen",
            side_effect=TimeoutError("timed out"),
        ),
        pytest.raises(AIProviderException) as exc_info,
    ):
        post_json("http://localhost:1234/v1/chat/completions", {}, {}, timeout=42)

    message = str(exc_info.value)
    assert "timed out after 42s" in message
    assert "ATLAS_AI_TIMEOUT_SECONDS" in message


def test_post_json_wrapped_timeout_gives_actionable_message() -> None:
    """A timeout wrapped in a URLError (the other path urlopen can take)
    must be diagnosed identically to a bare TimeoutError."""
    with (
        patch(
            "engine.ai.adapters._http.urlopen",
            side_effect=URLError(TimeoutError("timed out")),
        ),
        pytest.raises(AIProviderException) as exc_info,
    ):
        post_json("http://localhost:1234/v1/chat/completions", {}, {})

    assert "timed out after" in str(exc_info.value)


def test_post_json_401_gives_api_key_guidance() -> None:
    """RC-006 regression: an auth rejection must point at the API key, not
    just repeat the raw HTTP error."""
    error = HTTPError(
        url="https://api.example.com", code=401, msg="Unauthorized", hdrs=None, fp=None  # type: ignore[arg-type]
    )
    with (
        patch("engine.ai.adapters._http.urlopen", side_effect=error),
        pytest.raises(AIProviderException) as exc_info,
    ):
        post_json("https://api.example.com", {}, {})

    message = str(exc_info.value)
    assert "API key" in message
    assert "401" in message


def test_post_json_403_gives_api_key_guidance() -> None:
    error = HTTPError(
        url="https://api.example.com", code=403, msg="Forbidden", hdrs=None, fp=None  # type: ignore[arg-type]
    )
    with (
        patch("engine.ai.adapters._http.urlopen", side_effect=error),
        pytest.raises(AIProviderException, match="API key"),
    ):
        post_json("https://api.example.com", {}, {})


def test_post_json_500_is_not_treated_as_auth_failure() -> None:
    """A non-auth HTTP error must not get the API-key hint -- that would be
    actively misleading for e.g. a provider outage."""
    error = HTTPError(
        url="https://api.example.com",
        code=500,
        msg="Internal Server Error",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )
    with (
        patch("engine.ai.adapters._http.urlopen", side_effect=error),
        pytest.raises(AIProviderException) as exc_info,
    ):
        post_json("https://api.example.com", {}, {})

    message = str(exc_info.value)
    assert "API key" not in message
    assert "500" in message
