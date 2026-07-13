"""Exceptions for the Research subsystem."""


class ResearchException(Exception):
    """Base exception for Research subsystem errors."""


class ResearchNotFoundException(ResearchException):
    """Raised when research for a project cannot be found."""


class InvalidResearchOperationException(ResearchException):
    """Raised when an operation violates research business rules."""


class InvalidResearchException(ResearchException):
    """Raised when research data is corrupt or cannot be read from storage."""
