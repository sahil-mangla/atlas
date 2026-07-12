"""Exceptions for the Planning subsystem."""

class PlanningException(Exception):
    """Base exception for Planning subsystem errors."""
    pass

class PlanningNotFoundException(PlanningException):
    """Raised when planning for a project cannot be found."""
    pass

class InvalidPlanningOperationException(PlanningException):
    """Raised when an operation violates planning business rules (e.g. cycles, frozen state)."""
    pass
