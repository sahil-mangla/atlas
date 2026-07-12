"""ATLAS Memory System Subsystem.

The Memory System provides a persistent, hybrid append-only knowledge base
for ATLAS projects, preserving architectural decisions, research context,
planning milestones, and evaluation outcomes.
"""

from engine.memory.exceptions import (
    InvalidMemoryException,
    MemoryException,
    MemoryNotFoundException,
)
from engine.memory.fs_repository import FilesystemMemoryRepository
from engine.memory.repository import MemoryRepository
from engine.memory.serializers import (
    deserialize_entry,
    deserialize_memory,
    serialize_entry,
    serialize_memory,
)
from engine.memory.services import (
    MemoryCaptureService,
    MemoryOrganizationService,
    MemoryRetrievalService,
    MemoryVersioningService,
)

__all__ = [
    "FilesystemMemoryRepository",
    "InvalidMemoryException",
    "MemoryCaptureService",
    "MemoryException",
    "MemoryNotFoundException",
    "MemoryOrganizationService",
    "MemoryRepository",
    "MemoryRetrievalService",
    "MemoryVersioningService",
    "deserialize_entry",
    "deserialize_memory",
    "serialize_entry",
    "serialize_memory",
]
