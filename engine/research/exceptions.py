"""Exceptions for the Research subsystem."""

class ResearchException(Exception):
    """Base exception for Research subsystem errors."""
    pass

class ResearchNotFoundException(ResearchException):
    """Raised when research for a project cannot be found."""
    pass

class InvalidResearchOperationException(ResearchException):
    """Raised when an operation violates research business rules."""
    pass
