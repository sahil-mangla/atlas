"""Core domain models and schemas for the ATLAS platform.

This package exposes the complete, technology-independent domain language
of the project. No business logic, persistence, or infrastructure concerns
are contained here.
"""

from engine.domain.architecture import (
    ArchitecturalComponent,
    ArchitecturalDecision,
    Architecture,
)
from engine.domain.engineering_specification import EngineeringSpecification
from engine.domain.enums import (
    EvaluationStatus,
    FindingSeverity,
    Priority,
    ProjectStatus,
    ResearchStatus,
    TaskStatus,
    WorkflowStage,
)
from engine.domain.evaluation import (
    Evaluation,
    RequirementCoverage,
    ReviewFinding,
)
from engine.domain.memory import Memory, MemoryEntry
from engine.domain.project import Project
from engine.domain.research import (
    KnowledgeGap,
    Research,
    ResearchFinding,
    ResearchTopic,
)
from engine.domain.roadmap import Milestone, Roadmap, Task
from engine.domain.workflow import Workflow
from engine.domain.workspace import Workspace, WorkspaceArtifact

__all__ = [
    "ArchitecturalComponent",
    "ArchitecturalDecision",
    "Architecture",
    "EngineeringSpecification",
    "Evaluation",
    "EvaluationStatus",
    "FindingSeverity",
    "KnowledgeGap",
    "Memory",
    "MemoryEntry",
    "Milestone",
    "Priority",
    "Project",
    "ProjectStatus",
    "RequirementCoverage",
    "Research",
    "ResearchFinding",
    "ResearchStatus",
    "ResearchTopic",
    "ReviewFinding",
    "Roadmap",
    "Task",
    "TaskStatus",
    "Workflow",
    "WorkflowStage",
    "Workspace",
    "WorkspaceArtifact",
]
