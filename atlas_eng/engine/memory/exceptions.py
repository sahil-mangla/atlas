"""Exceptions for the ATLAS Memory System."""


class MemoryException(Exception):  # noqa: N818
    """Base exception for all memory subsystem errors."""


class MemoryNotFoundException(MemoryException):
    """Raised when a specific memory entry or project memory is not found."""


class InvalidMemoryException(MemoryException):
    """Raised when a memory artifact is corrupt or invalid."""
