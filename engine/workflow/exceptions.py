"""Exceptions for the ATLAS Workflow System."""


class WorkflowException(Exception):  # noqa: N818
    """Base exception for all workflow subsystem errors."""


class WorkflowNotFoundException(WorkflowException):
    """Raised when a specific project's workflow state is not found."""


class InvalidTransitionException(WorkflowException):
    """Raised when a transition violates state machine rules or approval status."""
