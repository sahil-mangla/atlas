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
from engine.domain.planning import (
    AcceptanceCriteria,
    DefinitionOfDone,
    EngineeringDeliverable,
    Planning,
    PlanningEpic,
    PlanningMilestone,
    PlanningSnapshot,
    PlanningSubtask,
    PlanningSummary,
    PlanningTask,
    ScopeDefinition,
)
from engine.domain.project import Project
from engine.domain.research import (
    Assumption,
    Constraint,
    Evidence,
    Opportunity,
    ProblemDefinition,
    Research,
    ResearchFinding,
    ResearchSnapshot,
    ResearchSource,
    ResearchSummary,
)
from engine.domain.roadmap import Milestone, Roadmap, Task
from engine.domain.workflow import ReadinessReview, Workflow, WorkflowHistoryEntry
from engine.domain.workspace import Workspace, WorkspaceArtifact

__all__ = [
    "AcceptanceCriteria",
    "ArchitecturalComponent",
    "ArchitecturalDecision",
    "Architecture",
    "Assumption",
    "Constraint",
    "DefinitionOfDone",
    "EngineeringDeliverable",
    "EngineeringSpecification",
    "Evaluation",
    "EvaluationStatus",
    "Evidence",
    "FindingSeverity",
    "Memory",
    "MemoryEntry",
    "Milestone",
    "Opportunity",
    "Planning",
    "PlanningEpic",
    "PlanningMilestone",
    "PlanningSnapshot",
    "PlanningStatus",
    "PlanningSubtask",
    "PlanningSummary",
    "PlanningTask",
    "Priority",
    "ProblemDefinition",
    "Project",
    "ProjectStatus",
    "ReadinessReview",
    "RequirementCoverage",
    "Research",
    "ResearchFinding",
    "ResearchSnapshot",
    "ResearchSource",
    "ResearchStatus",
    "ResearchSummary",
    "ReviewFinding",
    "Roadmap",
    "ScopeDefinition",
    "Task",
    "TaskStatus",
    "Workflow",
    "WorkflowHistoryEntry",
    "WorkflowStage",
    "Workspace",
    "WorkspaceArtifact",
]
