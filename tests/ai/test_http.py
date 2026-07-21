"""Unit tests for the shared post_json HTTP helper."""

import json
import logging
from unittest.mock import Mock, patch

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
