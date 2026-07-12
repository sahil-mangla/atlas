from engine.domain.enums import (
    EvaluationStatus,
    FindingSeverity,
    Priority,
    ProjectStatus,
    ResearchStatus,
    TaskStatus,
    WorkflowStage,
)


def test_project_status_values() -> None:
    assert ProjectStatus.INITIALIZED.value == "initialized"
    assert ProjectStatus.ACTIVE.value == "active"
    assert ProjectStatus.PAUSED.value == "paused"
    assert ProjectStatus.ARCHIVED.value == "archived"


def test_workflow_stage_values() -> None:
    assert WorkflowStage.IDEA.value == "idea"
    assert WorkflowStage.RESEARCH.value == "research"
    assert WorkflowStage.PROBLEM_DEFINITION.value == "problem_definition"
    assert WorkflowStage.PLANNING.value == "planning"
    assert WorkflowStage.ARCHITECTURE.value == "architecture"
    assert WorkflowStage.IMPLEMENTATION.value == "implementation"
    assert WorkflowStage.REVIEW.value == "review"
    assert WorkflowStage.ITERATION.value == "iteration"
    assert WorkflowStage.COMPLETION.value == "completion"


def test_priority_values() -> None:
    assert Priority.LOW.value == "low"
    assert Priority.MEDIUM.value == "medium"
    assert Priority.HIGH.value == "high"
    assert Priority.CRITICAL.value == "critical"


def test_evaluation_status_values() -> None:
    assert EvaluationStatus.PENDING.value == "pending"
    assert EvaluationStatus.PASSED.value == "passed"
    assert EvaluationStatus.PASSED_WITH_WARNINGS.value == "passed_with_warnings"
    assert EvaluationStatus.FAILED.value == "failed"


def test_research_status_values() -> None:
    assert ResearchStatus.DRAFT.value == "draft"
    assert ResearchStatus.IN_PROGRESS.value == "in_progress"
    assert ResearchStatus.READY_FOR_REVIEW.value == "ready_for_review"
    assert ResearchStatus.APPROVED.value == "approved"
    assert ResearchStatus.ARCHIVED.value == "archived"


def test_task_status_values() -> None:
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.IN_PROGRESS.value == "in_progress"
    assert TaskStatus.COMPLETE.value == "complete"
    assert TaskStatus.BLOCKED.value == "blocked"


def test_finding_severity_values() -> None:
    assert FindingSeverity.INFO.value == "info"
    assert FindingSeverity.WARNING.value == "warning"
    assert FindingSeverity.BLOCKING.value == "blocking"
