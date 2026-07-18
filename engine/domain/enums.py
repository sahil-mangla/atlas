"""Shared domain enumerations for the ATLAS platform.

All enumerations are defined here to provide a single source of truth for
domain state values used across every domain model.
"""

from enum import StrEnum


class ProjectStatus(StrEnum):
    """Operational lifecycle state of an engineering project."""

    INITIALIZED = "initialized"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class WorkflowStage(StrEnum):
    """Sequential stages of the ATLAS engineering lifecycle."""

    IDEA = "idea"
    RESEARCH = "research"
    PROBLEM_DEFINITION = "problem_definition"
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    ITERATION = "iteration"
    COMPLETION = "completion"


class Priority(StrEnum):
    """Execution urgency and ordering for tasks and milestones."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvaluationStatus(StrEnum):
    """Result state of a quality evaluation."""

    PENDING = "pending"
    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED = "failed"


class ResearchStatus(StrEnum):
    """Progress state of a research investigation."""

    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class PlanningStatus(StrEnum):
    """Progress state of project planning."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class ArchitectureStatus(StrEnum):
    """Progress state of project architecture design."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class TaskStatus(StrEnum):
    """Execution state of an implementation task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class FindingSeverity(StrEnum):
    """Severity classification of an evaluation finding."""

    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class FindingCategory(StrEnum):
    """Category of an evaluation finding."""

    TRACEABILITY = "traceability"
    ARCHITECTURE = "architecture"
    RISK = "risk"
    QUALITY = "quality"
    COMPLIANCE = "compliance"


class FindingLifecycleStatus(StrEnum):
    """Lifecycle state of an evaluation finding."""

    ACTIVE = "active"
    RESOLVED = "resolved"
    WAIVED = "waived"


class MemoryCategory(StrEnum):
    """Categorized domain division of engineering memory."""

    KNOWLEDGE = "knowledge"
    DECISION = "decision"
    CONTEXT = "context"
    ARTIFACT = "artifact"


class ApprovalStatus(StrEnum):
    """Human approval state for transitions in the workflow."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ConversationRole(StrEnum):
    """The role of a message participant."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ProposalStatus(StrEnum):
    """Lifecycle status of an AI proposal."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ProposalType(StrEnum):
    """Subsystem domain classification of a proposal."""

    RESEARCH = "research"
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    EVALUATION = "evaluation"
    MEMORY_CANDIDATE = "memory_candidate"
    KNOWLEDGE_CANDIDATE = "knowledge_candidate"


class ProposalDecision(StrEnum):
    """The formal engineering decision made by the human operator."""

    APPROVE = "approve"
    REJECT = "reject"


class KnowledgeCategory(StrEnum):
    PRINCIPLE = "principle"
    PATTERN = "pattern"
    STANDARD = "standard"
    CONVENTION = "convention"
    DECISION_SUMMARY = "decision_summary"
    CONSTRAINT = "constraint"
    LESSON_LEARNED = "lesson_learned"


class KnowledgeSourceType(StrEnum):
    RESEARCH_SNAPSHOT = "research_snapshot"
    PLANNING_SNAPSHOT = "planning_snapshot"
    ARCHITECTURE_SNAPSHOT = "architecture_snapshot"
    EVALUATION_SNAPSHOT = "evaluation_snapshot"
    HUMAN_SUBMISSION = "human_submission"
    ORGANIZATIONAL_IMPORT = "organizational_import"
    AI_PROPOSAL = "ai_proposal"


class KnowledgeCandidateStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class PublishedKnowledgeStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"


class KnowledgeActorType(StrEnum):
    HUMAN = "human"
    AI = "ai"
    SYSTEM = "system"
    WORKFLOW = "workflow"
    PLUGIN = "plugin"
    IMPORT = "import"
    EXTERNAL = "external"


class KnowledgeScope(StrEnum):
    PROJECT = "project"
    WORKSPACE = "workspace"
    ORGANIZATION = "organization"
