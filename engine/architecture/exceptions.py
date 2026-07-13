"""Exceptions for the Architecture subsystem."""


class ArchitectureException(Exception):
    """Base exception for Architecture subsystem errors."""


class ArchitectureNotFoundException(ArchitectureException):
    """Raised when architecture for a project cannot be found."""


class InvalidArchitectureOperationException(ArchitectureException):
    """Raised when an operation violates architecture business rules."""


class InvalidArchitectureException(ArchitectureException):
    """Raised when architecture data is corrupt or cannot be read from storage."""
