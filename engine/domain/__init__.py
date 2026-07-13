"""Core domain models and schemas for the ATLAS platform.

This package exposes the complete, technology-independent domain language
of the project. No business logic, persistence, or infrastructure concerns
are contained here.
"""

from engine.domain.architecture import (
    ArchitecturalDecision,
    Architecture,
    ArchitectureComponent,
    ArchitectureDriver,
    ArchitectureSnapshot,
    ArchitectureSummary,
    InterfaceContract,
    QualityAttribute,
    Risk,
    Constraint as ArchitectureConstraint,
    Assumption as ArchitectureAssumption,
)
from engine.domain.engineering_specification import EngineeringSpecification
from engine.domain.enums import (
    ArchitectureStatus,
    EvaluationStatus,
    FindingSeverity,
    PlanningStatus,
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
from engine.domain.metadata import ArtifactMetadata, ArtifactStatus
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
from engine.domain.review import EngineeringReview
from engine.domain.traceability import TraceabilityLink
from engine.domain.workflow import ReadinessReview, Workflow, WorkflowHistoryEntry
from engine.domain.workspace import Workspace, WorkspaceArtifact

__all__ = [
    "AcceptanceCriteria",
    "ArchitecturalDecision",
    "Architecture",
    "ArchitectureComponent",
    "ArchitectureDriver",
    "ArchitectureSnapshot",
    "ArchitectureStatus",
    "ArchitectureSummary",
    "ArtifactMetadata",
    "ArtifactStatus",
    "Assumption",
    "Constraint",
    "ArchitectureConstraint",
    "ArchitectureAssumption",
    "DefinitionOfDone",
    "EngineeringDeliverable",
    "EngineeringReview",
    "EngineeringSpecification",
    "Evaluation",
    "EvaluationStatus",
    "Evidence",
    "FindingSeverity",
    "InterfaceContract",
    "Memory",
    "MemoryEntry",
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
    "QualityAttribute",
    "ReadinessReview",
    "RequirementCoverage",
    "Research",
    "ResearchFinding",
    "ResearchSnapshot",
    "ResearchSource",
    "ResearchStatus",
    "ResearchSummary",
    "Risk",
    "ReviewFinding",
    "ScopeDefinition",
    "TaskStatus",
    "TraceabilityLink",
    "Workflow",
    "WorkflowHistoryEntry",
    "WorkflowStage",
    "Workspace",
    "WorkspaceArtifact",
]
