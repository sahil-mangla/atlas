"""Stable error contract for the ATLAS platform.

Wraps every ``ApplicationError`` subclass with an explicit, versioned error
code so out-of-process/protocol clients get a stable wire-level error
contract instead of a raw exception type name.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from atlas.exceptions import (
    AIProviderError,
    ApplicationError,
    BootstrapError,
    ContextAssemblyError,
    InvalidProjectError,
    InvalidTransitionError,
    ProjectAlreadyExistsError,
    ProjectLifecycleError,
    ProjectNotFoundError,
    ProposalValidationError,
    StageExecutionError,
    WorkflowNotReadyError,
)


class PlatformErrorCode(StrEnum):
    """Stable, versioned error codes exposed across the platform boundary.

    ``UNKNOWN_ERROR`` exists only as a defensive fallback inside
    ``to_error_envelope`` -- it is not a normal, expected outcome of any
    documented application error path. Every concrete ``ApplicationError``
    subclass has, and must always have, an explicit entry in
    ``_ERROR_CODE_MAP`` (enforced by
    ``tests/contracts/test_errors.py::test_all_application_errors_mapped``).
    Observing ``UNKNOWN_ERROR`` at runtime signals a programming defect --
    a new ``ApplicationError`` subclass added without a mapping entry, or an
    ``Atlas.handle()`` call with an unrecognized ``Command`` type -- never
    routine application behavior such as a not-found project or a failed
    validation, which all have dedicated codes.
    """

    PROJECT_NOT_FOUND = "project_not_found"
    PROJECT_ALREADY_EXISTS = "project_already_exists"
    INVALID_PROJECT = "invalid_project"
    PROJECT_LIFECYCLE_ERROR = "project_lifecycle_error"
    WORKFLOW_NOT_READY = "workflow_not_ready"
    INVALID_TRANSITION = "invalid_transition"
    STAGE_EXECUTION_ERROR = "stage_execution_error"
    PROPOSAL_VALIDATION_ERROR = "proposal_validation_error"
    CONTEXT_ASSEMBLY_ERROR = "context_assembly_error"
    AI_PROVIDER_ERROR = "ai_provider_error"
    BOOTSTRAP_ERROR = "bootstrap_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorEnvelope(BaseModel):
    """Stable, serializable representation of a platform-level error."""

    model_config = ConfigDict(frozen=True)

    code: PlatformErrorCode
    message: str
    retryable: bool = False


#: Single explicit literal mapping -- no reflection, no dynamic lookup.
_ERROR_CODE_MAP: dict[type[ApplicationError], PlatformErrorCode] = {
    ProjectNotFoundError: PlatformErrorCode.PROJECT_NOT_FOUND,
    ProjectAlreadyExistsError: PlatformErrorCode.PROJECT_ALREADY_EXISTS,
    InvalidProjectError: PlatformErrorCode.INVALID_PROJECT,
    ProjectLifecycleError: PlatformErrorCode.PROJECT_LIFECYCLE_ERROR,
    WorkflowNotReadyError: PlatformErrorCode.WORKFLOW_NOT_READY,
    InvalidTransitionError: PlatformErrorCode.INVALID_TRANSITION,
    StageExecutionError: PlatformErrorCode.STAGE_EXECUTION_ERROR,
    ProposalValidationError: PlatformErrorCode.PROPOSAL_VALIDATION_ERROR,
    ContextAssemblyError: PlatformErrorCode.CONTEXT_ASSEMBLY_ERROR,
    AIProviderError: PlatformErrorCode.AI_PROVIDER_ERROR,
    BootstrapError: PlatformErrorCode.BOOTSTRAP_ERROR,
}

#: Failure modes considered transient and safe to retry.
_RETRYABLE: frozenset[type[ApplicationError]] = frozenset({AIProviderError})


def to_error_envelope(exc: ApplicationError) -> ErrorEnvelope:
    """Translate an ``ApplicationError`` into a stable ``ErrorEnvelope``.

    Args:
        exc: The application error raised by a capability.

    Returns:
        The corresponding error envelope, falling back to ``UNKNOWN_ERROR``
        only for an unmapped exception type (see ``PlatformErrorCode`` docstring).
    """
    code = _ERROR_CODE_MAP.get(type(exc), PlatformErrorCode.UNKNOWN_ERROR)
    return ErrorEnvelope(code=code, message=str(exc), retryable=type(exc) in _RETRYABLE)
