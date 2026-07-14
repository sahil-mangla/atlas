"""Core domain models and schemas for the ATLAS platform.

This package exposes the complete, technology-independent domain language
of the project. No business logic, persistence, or infrastructure concerns
are contained here.
"""

from engine.domain.ai import (
    AIGenerationParameters,
    AIProposal,
    AIRequest,
    AIResponse,
    AIToolSchema,
    ContextPayload,
    PromptTemplateMetadata,
    ProviderCapabilities,
)
from engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    CommitResult,
    EvaluationProposalDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
from engine.domain.ai_feedback import ProposalFeedback
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
)
from engine.domain.architecture import (
    Assumption as ArchitectureAssumption,
)
from engine.domain.architecture import (
    Constraint as ArchitectureConstraint,
)
from engine.domain.conversation import (
    ConversationMessage,
    ConversationSession,
    MemoryCandidate,
)
from engine.domain.engineering_specification import EngineeringSpecification
from engine.domain.enums import (
    ArchitectureStatus,
    ConversationRole,
    EvaluationStatus,
    FindingCategory,
    FindingLifecycleStatus,
    FindingSeverity,
    PlanningStatus,
    Priority,
    ProjectStatus,
    ProposalDecision,
    ProposalStatus,
    ProposalType,
    ResearchStatus,
    TaskStatus,
    WorkflowStage,
)
from engine.domain.evaluation import (
    Evaluation,
    EvaluationFinding,
    EvaluationSnapshot,
    EvaluationSummary,
    ReadinessDecision,
    RequirementCoverage,
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
    "AIGenerationParameters",
    "AIProposal",
    "AIRequest",
    "AIResponse",
    "AIToolSchema",
    "AcceptanceCriteria",
    "ArchitecturalDecision",
    "Architecture",
    "ArchitectureAssumption",
    "ArchitectureComponent",
    "ArchitectureConstraint",
    "ArchitectureDriver",
    "ArchitectureProposalDraft",
    "ArchitectureSnapshot",
    "ArchitectureStatus",
    "ArchitectureSummary",
    "ArtifactMetadata",
    "ArtifactStatus",
    "Assumption",
    "CommitResult",
    "Constraint",
    "ContextPayload",
    "ConversationMessage",
    "ConversationRole",
    "ConversationSession",
    "DefinitionOfDone",
    "EngineeringDeliverable",
    "EngineeringReview",
    "EngineeringSpecification",
    "Evaluation",
    "EvaluationFinding",
    "EvaluationProposalDraft",
    "EvaluationSnapshot",
    "EvaluationStatus",
    "EvaluationSummary",
    "Evidence",
    "FindingCategory",
    "FindingLifecycleStatus",
    "FindingSeverity",
    "InterfaceContract",
    "Memory",
    "MemoryCandidate",
    "MemoryEntry",
    "Opportunity",
    "Planning",
    "PlanningEpic",
    "PlanningMilestone",
    "PlanningProposalDraft",
    "PlanningSnapshot",
    "PlanningStatus",
    "PlanningSubtask",
    "PlanningSummary",
    "PlanningTask",
    "Priority",
    "ProblemDefinition",
    "Project",
    "ProjectStatus",
    "PromptTemplateMetadata",
    "ProposalDecision",
    "ProposalFeedback",
    "ProposalStatus",
    "ProposalType",
    "ProviderCapabilities",
    "QualityAttribute",
    "ReadinessDecision",
    "ReadinessReview",
    "RequirementCoverage",
    "Research",
    "ResearchFinding",
    "ResearchProposalDraft",
    "ResearchSnapshot",
    "ResearchSource",
    "ResearchStatus",
    "ResearchSummary",
    "Risk",
    "ScopeDefinition",
    "TaskStatus",
    "TraceabilityLink",
    "Workflow",
    "WorkflowHistoryEntry",
    "WorkflowStage",
    "Workspace",
    "WorkspaceArtifact",
]
