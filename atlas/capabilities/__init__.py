"""ATLAS platform capability layer.

Internal implementation detail of the ``Atlas`` facade -- not part of the
public SDK surface and never imported by client adapters directly (clients
only ever see ``Atlas``, per ADR-002). Decomposes the facade into five
narrow, independently testable delegation objects. See the Capability
Responsibility Rule in ``docs/plans/phase-15-platform-layer.md`` §3.5.
"""

from atlas.capabilities.knowledge_capability import KnowledgeCapability
from atlas.capabilities.presentation_capability import PresentationCapability
from atlas.capabilities.project_capability import ProjectCapability
from atlas.capabilities.workflow_capability import WorkflowCapability
from atlas.capabilities.workflow_execution_capability import WorkflowExecutionCapability

__all__ = [
    "KnowledgeCapability",
    "PresentationCapability",
    "ProjectCapability",
    "WorkflowCapability",
    "WorkflowExecutionCapability",
]
