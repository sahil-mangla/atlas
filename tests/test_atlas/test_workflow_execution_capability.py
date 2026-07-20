"""Unit tests for WorkflowExecutionCapability's internal exception mapping.

Phase 15 post-implementation audit finding: this capability's
_map_workflow_exception initially dropped the InvalidTransitionException
branch present in the pre-Phase-15 shared Atlas._map_workflow_exception.
No current call site in this capability triggers that branch (dormant),
so the equivalence tests against Atlas's public methods could not catch
it. This test exercises the mapping method directly to close that gap.
"""

from unittest.mock import MagicMock

from atlas.capabilities.workflow_execution_capability import (
    WorkflowExecutionCapability,
)
from atlas.exceptions import (
    ApplicationError,
    InvalidTransitionError,
    WorkflowNotReadyError,
)
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowException,
    WorkflowNotFoundException,
)


def _capability() -> WorkflowExecutionCapability:
    return WorkflowExecutionCapability(
        workflow_repo=MagicMock(),
        orchestration_service=MagicMock(),
        proposal_repo=MagicMock(),
    )


def test_map_workflow_exception_maps_not_found() -> None:
    capability = _capability()
    result = capability._map_workflow_exception(WorkflowNotFoundException("x"))
    assert isinstance(result, WorkflowNotReadyError)


def test_map_workflow_exception_maps_invalid_transition() -> None:
    """Regression test for the audit-found parity gap."""
    capability = _capability()
    result = capability._map_workflow_exception(InvalidTransitionException("x"))
    assert isinstance(result, InvalidTransitionError)


def test_map_workflow_exception_maps_generic_workflow_exception() -> None:
    capability = _capability()
    result = capability._map_workflow_exception(WorkflowException("x"))
    assert type(result) is ApplicationError
