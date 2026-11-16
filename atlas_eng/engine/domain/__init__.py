"""Core domain models and schemas for the ATLAS platform.

This package exposes the complete, technology-independent domain language
of the project. No business logic, persistence, or infrastructure concerns
are contained here.
"""

from atlas_eng.engine.domain.ai import (
    AIGenerationParameters,
    AIProposal,
    AIRequest,
    AIResponse,
    AIToolSchema,
    ContextPayload,
    PromptTemplateMetadata,
    ProviderCapabilities,
)
from atlas_eng.engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    CommitResult,
    EvaluationProposalDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
from atlas_eng.engine.domain.ai_feedback import ProposalFeedback
from atlas_eng.engine.domain.architecture import (
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
from atlas_eng.engine.domain.architecture import (
    Assumption as ArchitectureAssumption,
)
from atlas_eng.engine.domain.architecture import (
    Constraint as ArchitectureConstraint,
)
from atlas_eng.engine.domain.conversation import (
    ConversationMessage,
    ConversationSession,
    MemoryCandidate,
)
from atlas_eng.engine.domain.engineering_specification import EngineeringSpecification
from atlas_eng.engine.domain.enums import (
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
from atlas_eng.engine.domain.evaluation import (
    Evaluation,
    EvaluationFinding,
    EvaluationSnapshot,
    EvaluationSummary,
    ReadinessDecision,
    RequirementCoverage,
)
from atlas_eng.engine.domain.memory import Memory, MemoryEntry
from atlas_eng.engine.domain.metadata import ArtifactMetadata, ArtifactStatus
from atlas_eng.engine.domain.planning import (
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
from atlas_eng.engine.domain.project import Project
from atlas_eng.engine.domain.research import (
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
from atlas_eng.engine.domain.review import EngineeringReview
from atlas_eng.engine.domain.traceability import TraceabilityLink
from atlas_eng.engine.domain.workflow import (
    ReadinessReview,
    Workflow,
    WorkflowHistoryEntry,
)
from atlas_eng.engine.domain.workspace import Workspace, WorkspaceArtifact

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
