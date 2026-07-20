"""Tests for atlas.contracts.envelope -- RequestEnvelope/ResponseEnvelope."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from atlas.adapters.protocol import AdapterContext, AdapterKind
from atlas.commands import ListProjectsCommand
from atlas.contracts.envelope import RequestEnvelope, ResponseEnvelope
from atlas.contracts.errors import ErrorEnvelope, PlatformErrorCode
from atlas.contracts.version import PLATFORM_API_VERSION
from atlas.results import OperationResult


def _adapter_context() -> AdapterContext:
    return AdapterContext(kind=AdapterKind.AI, name="test-agent", version="0.1.0")


def test_request_envelope_defaults_api_version_and_request_id() -> None:
    envelope = RequestEnvelope(
        adapter=_adapter_context(), command=ListProjectsCommand()
    )
    assert envelope.api_version == PLATFORM_API_VERSION
    assert envelope.request_id is not None


def test_request_envelope_is_frozen() -> None:
    envelope = RequestEnvelope(
        adapter=_adapter_context(), command=ListProjectsCommand()
    )
    with pytest.raises(ValidationError):
        envelope.command = ListProjectsCommand()


def test_response_envelope_accepts_result_only() -> None:
    envelope = ResponseEnvelope(
        request_id=uuid4(),
        result=OperationResult(success=True, message="ok"),
    )
    assert envelope.result is not None
    assert envelope.error is None


def test_response_envelope_accepts_error_only() -> None:
    envelope: ResponseEnvelope[OperationResult] = ResponseEnvelope(
        request_id=uuid4(),
        error=ErrorEnvelope(code=PlatformErrorCode.UNKNOWN_ERROR, message="x"),
    )
    assert envelope.error is not None
    assert envelope.result is None


def test_response_envelope_rejects_both_set() -> None:
    with pytest.raises(ValidationError):
        ResponseEnvelope(
            request_id=uuid4(),
            result=OperationResult(success=True),
            error=ErrorEnvelope(code=PlatformErrorCode.UNKNOWN_ERROR, message="x"),
        )


def test_response_envelope_rejects_neither_set() -> None:
    with pytest.raises(ValidationError):
        ResponseEnvelope(request_id=uuid4())


def test_response_envelope_is_frozen() -> None:
    envelope = ResponseEnvelope(
        request_id=uuid4(), result=OperationResult(success=True)
    )
    with pytest.raises(ValidationError):
        envelope.result = None
