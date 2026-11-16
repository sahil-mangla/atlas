"""Exceptions for the Evaluation subsystem."""


class EvaluationException(Exception):  # noqa: N818
    """Base exception for Evaluation subsystem errors."""


class EvaluationNotFoundException(EvaluationException):
    """Raised when evaluation for a project cannot be found."""


class InvalidEvaluationOperationException(EvaluationException):
    """Raised when an operation violates evaluation business rules."""


class InvalidEvaluationException(EvaluationException):
    """Raised when evaluation data is corrupt or cannot be read from storage."""
