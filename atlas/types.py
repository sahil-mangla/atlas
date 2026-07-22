"""Stable scalar types exposed by the Atlas SDK."""

from enum import StrEnum


class ProjectStatus(StrEnum):
    INITIALIZED = "initialized"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class WorkflowStage(StrEnum):
    IDEA = "idea"
    RESEARCH = "research"
    PROBLEM_DEFINITION = "problem_definition"
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    ITERATION = "iteration"
    COMPLETION = "completion"


class ProposalStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class EvaluationStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED = "failed"


class ProposalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class KnowledgeActorType(StrEnum):
    HUMAN = "human"
    AI = "ai"
    SYSTEM = "system"
    WORKFLOW = "workflow"
    PLUGIN = "plugin"
    IMPORT = "import"
    EXTERNAL = "external"


class KnowledgeCandidateStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
