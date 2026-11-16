"""Exceptions for the Planning subsystem."""


class PlanningException(Exception):  # noqa: N818
    """Base exception for Planning subsystem errors."""


class PlanningNotFoundException(PlanningException):
    """Raised when planning for a project cannot be found."""


class InvalidPlanningOperationException(PlanningException):
    """Raised when an operation violates planning rules (e.g. cycles, frozen state)."""


class InvalidPlanningException(PlanningException):
    """Raised when planning data is corrupt or cannot be read from storage."""
