"""ATLAS Project Subsystem.

Provides the services, models, repositories, and exceptions for managing
project lifecycles, configuration metadata, and workspaces.
"""

from engine.project.exceptions import (
    InvalidProjectException,
    ProjectAlreadyExistsException,
    ProjectException,
    ProjectLifecycleException,
    ProjectNotFoundException,
)
from engine.project.fs_repository import FilesystemProjectRepository
from engine.project.repository import ProjectRepository
from engine.project.services import (
    ProjectCreationService,
    ProjectLifecycleService,
    ProjectLoadingService,
    ProjectRegistryService,
)

__all__ = [
    "FilesystemProjectRepository",
    "InvalidProjectException",
    "ProjectAlreadyExistsException",
    "ProjectCreationService",
    "ProjectException",
    "ProjectLifecycleException",
    "ProjectLifecycleService",
    "ProjectLoadingService",
    "ProjectNotFoundException",
    "ProjectRegistryService",
    "ProjectRepository",
]
