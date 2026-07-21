"""Unit tests for the workflow domain models."""

from datetime import UTC, datetime
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


# ---------------------------------------------------------------------------
# S-01: Timestamp consistency — P-03: Backward transition accounting
# ---------------------------------------------------------------------------


def test_workflow_history_entry_timestamp_is_utc_aware() -> None:
    """S-01: WorkflowHistoryEntry.timestamp must be timezone-aware UTC."""
    entry = WorkflowHistoryEntry(
        previous_stage=WorkflowStage.IDEA,
        new_stage=WorkflowStage.RESEARCH,
        approval_status=ApprovalStatus.APPROVED,
        reason="Test",
    )

    assert entry.timestamp.tzinfo is not None, (
        "timestamp must be timezone-aware (was naive — utcnow() regression)"
    )
    assert entry.timestamp.tzinfo == UTC or entry.timestamp.utcoffset() is not None


def test_readiness_review_generated_at_is_utc_aware() -> None:
    """S-01: ReadinessReview.generated_at must be timezone-aware UTC."""
    review = ReadinessReview(
        stage=WorkflowStage.RESEARCH,
        status=EvaluationStatus.PASSED,
        completed_objectives=[],
        blocking_issues=[],
        optional_improvements=[],
        confidence=1.0,
    )

    assert review.generated_at.tzinfo is not None, (
        "generated_at must be timezone-aware (was naive — utcnow() regression)"
    )
    assert review.generated_at.utcoffset() is not None


def test_workflow_backward_transition_preserves_completed_stages() -> None:
    """P-03: Backward transitions must not corrupt completed_stages accounting.

    Scenario: IDEA -> RESEARCH (forward) -> IDEA (backward)
    completed_stages must still contain IDEA after the backward step.
    RESEARCH must NOT appear in completed_stages (it was not forward-completed).
    """
    workflow = Workflow(project_id=uuid4())

    # Forward: IDEA → RESEARCH
    forward = WorkflowHistoryEntry(
        previous_stage=WorkflowStage.IDEA,
        new_stage=WorkflowStage.RESEARCH,
        approval_status=ApprovalStatus.APPROVED,
        reason="Proceeding to research",
    )
    workflow.record_transition(forward)

    assert workflow.current_stage == WorkflowStage.RESEARCH
    assert WorkflowStage.IDEA in workflow.completed_stages

    # Backward: RESEARCH → IDEA
    backward = WorkflowHistoryEntry(
        previous_stage=WorkflowStage.RESEARCH,
        new_stage=WorkflowStage.IDEA,
        approval_status=ApprovalStatus.APPROVED,
        reason="Back to refine idea",
    )
    workflow.record_transition(backward)

    assert workflow.current_stage == WorkflowStage.IDEA  # type: ignore[comparison-overlap]
    # IDEA remains in completed_stages (it was genuinely forward-completed)
    assert WorkflowStage.IDEA in workflow.completed_stages  # type: ignore[unreachable]
    # RESEARCH was not forward-completed — must not be in completed_stages
    assert WorkflowStage.RESEARCH not in workflow.completed_stages
    # Both transitions are in history
    assert len(workflow.history) == 2


def test_workflow_forward_then_backward_then_forward_again() -> None:
    """P-03: A second forward pass from a backward position correctly appends."""
    workflow = Workflow(project_id=uuid4())

    def _transition(prev: WorkflowStage, nxt: WorkflowStage) -> None:
        workflow.record_transition(
            WorkflowHistoryEntry(
                previous_stage=prev,
                new_stage=nxt,
                approval_status=ApprovalStatus.APPROVED,
                reason="test",
            )
        )

    _transition(WorkflowStage.IDEA, WorkflowStage.RESEARCH)  # forward
    _transition(WorkflowStage.RESEARCH, WorkflowStage.IDEA)  # backward
    _transition(WorkflowStage.IDEA, WorkflowStage.RESEARCH)  # forward again

    # After second forward IDEA→RESEARCH:
    # IDEA should be in completed_stages exactly once
    assert workflow.completed_stages.count(WorkflowStage.IDEA) == 1
    assert workflow.current_stage == WorkflowStage.RESEARCH
    assert len(workflow.history) == 3


def test_workflow_skipped_stage_marked_completed_and_not_left_pending() -> None:
    """Regression test (Finding-009): a direct transition that legally skips
    a stage (e.g. RESEARCH -> PLANNING, skipping PROBLEM_DEFINITION, since
    PROBLEM_DEFINITION has no AI-generation support) must mark the skipped
    stage completed too -- otherwise it lingers in pending_stages forever
    and a later automatic "next stage" lookup would incorrectly select it."""
    workflow = Workflow(project_id=uuid4())

    def _transition(prev: WorkflowStage, nxt: WorkflowStage) -> None:
        workflow.record_transition(
            WorkflowHistoryEntry(
                previous_stage=prev,
                new_stage=nxt,
                approval_status=ApprovalStatus.APPROVED,
                reason="test",
            )
        )

    _transition(WorkflowStage.IDEA, WorkflowStage.RESEARCH)
    _transition(
        WorkflowStage.RESEARCH, WorkflowStage.PLANNING
    )  # skips PROBLEM_DEFINITION -- no AI executor for it.

    assert workflow.current_stage == WorkflowStage.PLANNING
    assert WorkflowStage.IDEA in workflow.completed_stages
    assert WorkflowStage.RESEARCH in workflow.completed_stages
    assert WorkflowStage.PROBLEM_DEFINITION in workflow.completed_stages
    assert WorkflowStage.PROBLEM_DEFINITION not in workflow.pending_stages
    assert workflow.pending_stages[0] == WorkflowStage.ARCHITECTURE


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
    assert review.confidence == 0.95
    assert isinstance(review.generated_at, datetime)
