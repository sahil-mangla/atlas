"""AI Integration subsystem exceptions."""


class AIException(Exception):
    """Base exception for AI Integration subsystem errors."""


class AIProviderException(AIException):
    """Raised when the underlying AI Provider encounters an error."""


class ConversationNotFoundException(AIException):
    """Raised when a specific conversation session cannot be found."""


class InvalidConversationException(AIException):
    """Raised when a conversation is corrupt or invalid."""


class InvalidContextException(AIException):
    """Raised when context assembly fails due to missing or invalid snapshots."""


class InvalidProposalException(AIException):
    """Raised when an AI proposal fails domain validation or parsing."""
