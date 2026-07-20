"""Shared capability naming for the ATLAS platform capability layer.

This module contains only the ``CapabilityName`` enum -- the single source
of truth for naming capabilities anywhere they are referenced (the adapter
negotiation manifest, the capability ownership matrix, self-identification
on each capability class). No capability logic lives here.
"""

from enum import StrEnum


class CapabilityName(StrEnum):
    """Identifies one of the five platform capability boundaries."""

    PROJECT = "project"
    WORKFLOW = "workflow"
    WORKFLOW_EXECUTION = "workflow_execution"
    KNOWLEDGE = "knowledge"
    PRESENTATION = "presentation"
