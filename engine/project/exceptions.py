"""Custom exceptions for the ATLAS Project System."""


class ProjectException(Exception):  # noqa: N818
    """Base exception for all Project System errors."""


class ProjectNotFoundException(ProjectException):
    """Raised when a requested project cannot be found in the repository."""


class ProjectAlreadyExistsException(ProjectException):
    """Raised when trying to create a project where one already exists."""


class InvalidProjectException(ProjectException):
    """Raised when project metadata is corrupt, invalid, or cannot be parsed."""


class ProjectLifecycleException(ProjectException):
    """Raised when an invalid lifecycle transition or modification is attempted."""
