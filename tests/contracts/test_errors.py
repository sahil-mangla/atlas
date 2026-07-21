"""Tests for atlas.contracts.errors -- the platform error contract."""

import pytest

from atlas.contracts.errors import (
    _ERROR_CODE_MAP,
    ErrorEnvelope,
    PlatformErrorCode,
    to_error_envelope,
)
from atlas.exceptions import (
    AIProviderError,
    ApplicationError,
    BootstrapError,
    ProjectNotFoundError,
)


def test_all_application_errors_mapped() -> None:
    """Every concrete ApplicationError subclass must have an explicit error code.

    This is the dedicated architectural test required by the Phase 15 plan:
    it fails whenever a new ApplicationError subclass is introduced without a
    corresponding entry in _ERROR_CODE_MAP, so UNKNOWN_ERROR is never silently
    reached for an exception type that exists in the codebase.
    """
    concrete_subclasses = {
        cls for cls in ApplicationError.__subclasses__() if cls is not ApplicationError
    }
    unmapped = concrete_subclasses - set(_ERROR_CODE_MAP.keys())
    assert not unmapped, f"ApplicationError subclasses missing error codes: {unmapped}"


_EXPECTED_ERROR_CODE_COUNT = 12


def test_error_code_map_has_eleven_entries() -> None:
    assert len(_ERROR_CODE_MAP) == _EXPECTED_ERROR_CODE_COUNT


def test_to_error_envelope_maps_project_not_found() -> None:
    envelope = to_error_envelope(ProjectNotFoundError("missing"))
    assert envelope.code == PlatformErrorCode.PROJECT_NOT_FOUND
    assert envelope.message == "missing"


def test_to_error_envelope_marks_ai_provider_error_retryable() -> None:
    envelope = to_error_envelope(AIProviderError("transient"))
    assert envelope.retryable is True


def test_to_error_envelope_marks_others_not_retryable() -> None:
    envelope = to_error_envelope(BootstrapError("boom"))
    assert envelope.retryable is False


def test_error_envelope_is_frozen() -> None:
    envelope = ErrorEnvelope(code=PlatformErrorCode.UNKNOWN_ERROR, message="x")
    with pytest.raises(Exception):  # noqa: B017
        envelope.message = "y"
