"""Application-level exceptions for the ATLAS public SDK."""


class ApplicationError(Exception):
    """Base exception for all ATLAS Application Platform Layer errors."""


class ProjectNotFoundError(ApplicationError):
    """Raised when a requested project cannot be found."""


class ProjectAlreadyExistsError(ApplicationError):
    """Raised when trying to create a project where one already exists."""


class InvalidProjectError(ApplicationError):
    """Raised when project metadata is corrupt or invalid."""


class ProjectLifecycleError(ApplicationError):
    """Raised when an invalid project lifecycle transition is attempted."""


class WorkflowNotReadyError(ApplicationError):
    """Raised when workflow prerequisites are not met."""


class InvalidTransitionError(ApplicationError):
    """Raised when a transition violates state machine rules or approval status."""


class StageExecutionError(ApplicationError):
    """Raised when executing an AI stage fails."""


class ProposalValidationError(ApplicationError):
    """Raised when an AI proposal fails domain validation or parsing."""


class ContextAssemblyError(ApplicationError):
    """Raised when context assembly fails due to missing or invalid snapshots."""


class AIProviderError(ApplicationError):
    """Raised when the underlying AI Provider encounters an error."""


class KnowledgeReviewError(ApplicationError):
    """Raised when a human review of an engineering-knowledge candidate fails."""


class BootstrapError(ApplicationError):
    """Raised when the platform fails to initialize correctly."""
