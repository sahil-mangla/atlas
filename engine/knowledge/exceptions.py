class KnowledgeException(Exception):  # noqa: N818
    """Base exception for the engineering knowledge subsystem."""


class InvalidKnowledgeException(KnowledgeException):
    """Raised when persisted knowledge is invalid or corrupt."""


class KnowledgeReviewException(KnowledgeException):
    """Raised when a candidate review violates lifecycle rules."""
