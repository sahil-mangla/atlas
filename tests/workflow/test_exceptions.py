"""Unit tests for the workflow exceptions."""

from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowException,
    WorkflowNotFoundException,
)


def test_workflow_exception_hierarchy() -> None:
    assert issubclass(WorkflowNotFoundException, WorkflowException)
    assert issubclass(InvalidTransitionException, WorkflowException)
    assert issubclass(WorkflowException, Exception)


def test_exceptions_instantiation() -> None:
    e = InvalidTransitionException("illegal move")
    assert str(e) == "illegal move"
