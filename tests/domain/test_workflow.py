"""Unit tests for the workflow domain models."""

from datetime import datetime
from uuid import UUID, uuid4

from engine.domain.enums import ApprovalStatus, EvaluationStatus, WorkflowStage
from engine.domain.workflow import ReadinessReview, Workflow, WorkflowHistoryEntry


def test_workflow_defaults() -> None:
    project_id = uuid4()
    workflow = Workflow(project_id=project_id)

    assert isinstance(workflow.id, UUID)
    assert workflow.project_id == project_id
    assert workflow.current_stage == WorkflowStage.IDEA
    assert workflow.completed_stages == []
    assert workflow.pending_stages == []
    assert workflow.active_objectives == []
    assert workflow.history == []


def test_workflow_record_transition() -> None:
    project_id = uuid4()
    workflow = Workflow(project_id=project_id)

    entry = WorkflowHistoryEntry(
        previous_stage=WorkflowStage.IDEA,
        new_stage=WorkflowStage.RESEARCH,
        approval_status=ApprovalStatus.APPROVED,
        reason="Approved by PM",
        confidence=0.9,
    )

    workflow.record_transition(entry)

    assert workflow.current_stage == WorkflowStage.RESEARCH
    assert workflow.completed_stages == [WorkflowStage.IDEA]
    assert workflow.pending_stages == list(WorkflowStage)[2:]
    assert len(workflow.history) == 1
    assert workflow.history[0].new_stage == WorkflowStage.RESEARCH


def test_readiness_review_defaults() -> None:
    review = ReadinessReview(
        stage=WorkflowStage.RESEARCH,
        status=EvaluationStatus.PASSED,
        completed_objectives=["Review literature"],
        blocking_issues=[],
        optional_improvements=["Check more citations"],
        confidence=0.95,
    )

    assert review.stage == WorkflowStage.RESEARCH
    assert review.status == EvaluationStatus.PASSED
    assert review.completed_objectives == ["Review literature"]
    assert review.blocking_issues == []
    assert review.optional_improvements == ["Check more citations"]
    assert review.confidence == 0.95  # noqa: PLR2004
    assert isinstance(review.generated_at, datetime)
