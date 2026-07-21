"""Unit tests for the workflow subsystem services."""

from uuid import UUID, uuid4

import pytest

from engine.domain.enums import ApprovalStatus, EvaluationStatus, WorkflowStage
from engine.domain.workflow import Workflow
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowNotFoundException,
)
from engine.workflow.repository import WorkflowRepository
from engine.workflow.services import (
    WorkflowHistoryService,
    WorkflowInitializationService,
    WorkflowProgressService,
    WorkflowReadinessService,
    WorkflowTransitionService,
)


class FakeWorkflowRepository(WorkflowRepository):
    def __init__(self) -> None:
        self.workflows: dict[str, Workflow] = {}

    def save(self, workflow: Workflow) -> None:
        self.workflows[str(workflow.project_id)] = workflow

    def get_by_project_id(self, project_id: UUID) -> Workflow | None:
        return self.workflows.get(str(project_id))

    def exists(self, project_id: UUID) -> bool:
        return str(project_id) in self.workflows


@pytest.fixture
def repo() -> FakeWorkflowRepository:
    return FakeWorkflowRepository()


def test_workflow_initialization_service(repo: FakeWorkflowRepository) -> None:
    service = WorkflowInitializationService(repo)
    project_id = uuid4()

    workflow = service.initialize_workflow(project_id)

    assert workflow.project_id == project_id
    assert workflow.current_stage == WorkflowStage.IDEA
    # IDEA starts with no active objectives: its objectives are already
    # satisfied by the description/objective supplied at project creation.
    assert workflow.active_objectives == []
    assert repo.exists(project_id) is True


def test_workflow_progress_service(repo: FakeWorkflowRepository) -> None:
    init = WorkflowInitializationService(repo)
    progress = WorkflowProgressService(repo)
    project_id = uuid4()

    init.initialize_workflow(project_id)

    # Set objectives
    progress.set_active_objectives(project_id, ["Task A", "Task B"])
    workflow = repo.get_by_project_id(project_id)
    assert workflow is not None
    assert workflow.active_objectives == ["Task A", "Task B"]

    # Complete objective
    progress.complete_objective(project_id, "Task A")
    assert workflow.active_objectives == ["Task B"]


def test_workflow_progress_service_not_found(repo: FakeWorkflowRepository) -> None:
    progress = WorkflowProgressService(repo)
    with pytest.raises(WorkflowNotFoundException):
        progress.set_active_objectives(uuid4(), [])
    with pytest.raises(WorkflowNotFoundException):
        progress.complete_objective(uuid4(), "test")


def test_workflow_readiness_service(repo: FakeWorkflowRepository) -> None:
    init = WorkflowInitializationService(repo)
    progress = WorkflowProgressService(repo)
    readiness = WorkflowReadinessService(repo)
    project_id = uuid4()

    init.initialize_workflow(project_id)

    # IDEA starts with no active objectives, so it's auto-ready.
    review = readiness.evaluate_readiness(project_id)
    assert review.stage == WorkflowStage.IDEA
    assert review.status == EvaluationStatus.PASSED
    assert len(review.blocking_issues) == 0
    assert review.confidence == 1.0

    # Setting objectives manually blocks readiness again.
    progress.set_active_objectives(project_id, ["Task A"])
    review = readiness.evaluate_readiness(project_id)
    assert review.status == EvaluationStatus.FAILED
    assert len(review.blocking_issues) > 0
    assert review.confidence < 1.0

    # Clear objectives
    progress.set_active_objectives(project_id, [])
    review = readiness.evaluate_readiness(project_id)
    assert review.status == EvaluationStatus.PASSED
    assert len(review.blocking_issues) == 0
    assert review.confidence == 1.0


def test_workflow_readiness_service_not_found(repo: FakeWorkflowRepository) -> None:
    readiness = WorkflowReadinessService(repo)
    with pytest.raises(WorkflowNotFoundException):
        readiness.evaluate_readiness(uuid4())


def test_workflow_transition_service(repo: FakeWorkflowRepository) -> None:
    init = WorkflowInitializationService(repo)
    transition_srv = WorkflowTransitionService(repo)
    project_id = uuid4()

    init.initialize_workflow(project_id)

    # Transition IDEA -> RESEARCH (approved)
    workflow = transition_srv.transition_stage(
        project_id=project_id,
        new_stage=WorkflowStage.RESEARCH,
        approval_status=ApprovalStatus.APPROVED,
        reason="Initial research approved by team",
        confidence=0.9,
    )

    assert workflow.current_stage == WorkflowStage.RESEARCH
    assert len(workflow.history) == 1
    assert workflow.history[0].approval_status == ApprovalStatus.APPROVED
    assert workflow.history[0].previous_stage == WorkflowStage.IDEA
    assert workflow.history[0].new_stage == WorkflowStage.RESEARCH


def test_workflow_transition_service_illegal_move(repo: FakeWorkflowRepository) -> None:
    init = WorkflowInitializationService(repo)
    transition_srv = WorkflowTransitionService(repo)
    project_id = uuid4()

    init.initialize_workflow(project_id)

    # Illegal transition: IDEA -> IMPLEMENTATION
    with pytest.raises(InvalidTransitionException, match="illegal"):
        transition_srv.transition_stage(
            project_id=project_id,
            new_stage=WorkflowStage.IMPLEMENTATION,
            approval_status=ApprovalStatus.APPROVED,
            reason="Skipping steps",
        )


def test_workflow_transition_service_allows_skipping_stages_with_no_executor(
    repo: FakeWorkflowRepository,
) -> None:
    """Regression test (Finding-009): RESEARCH -> PLANNING and
    ARCHITECTURE -> REVIEW must be legal direct transitions, since
    PROBLEM_DEFINITION and IMPLEMENTATION have no registered AI executor and
    are not mandatory waypoints."""
    init = WorkflowInitializationService(repo)
    transition_srv = WorkflowTransitionService(repo)
    project_id = uuid4()

    init.initialize_workflow(project_id)
    transition_srv.transition_stage(
        project_id=project_id,
        new_stage=WorkflowStage.RESEARCH,
        approval_status=ApprovalStatus.APPROVED,
        reason="test",
    )

    workflow = transition_srv.transition_stage(
        project_id=project_id,
        new_stage=WorkflowStage.PLANNING,
        approval_status=ApprovalStatus.APPROVED,
        reason="Skipping problem_definition -- no AI executor for it.",
    )
    assert workflow.current_stage == WorkflowStage.PLANNING

    workflow = transition_srv.transition_stage(
        project_id=project_id,
        new_stage=WorkflowStage.ARCHITECTURE,
        approval_status=ApprovalStatus.APPROVED,
        reason="test",
    )
    assert workflow.current_stage == WorkflowStage.ARCHITECTURE

    workflow = transition_srv.transition_stage(
        project_id=project_id,
        new_stage=WorkflowStage.REVIEW,
        approval_status=ApprovalStatus.APPROVED,
        reason="Skipping implementation -- no AI executor for it.",
    )
    assert workflow.current_stage == WorkflowStage.REVIEW


def test_workflow_transition_service_unapproved(repo: FakeWorkflowRepository) -> None:
    init = WorkflowInitializationService(repo)
    transition_srv = WorkflowTransitionService(repo)
    project_id = uuid4()

    init.initialize_workflow(project_id)

    # Transition pending approval (fails)
    with pytest.raises(InvalidTransitionException, match="without explicit approval"):
        transition_srv.transition_stage(
            project_id=project_id,
            new_stage=WorkflowStage.RESEARCH,
            approval_status=ApprovalStatus.PENDING,
            reason="Pending review",
        )


def test_workflow_transition_service_not_found(repo: FakeWorkflowRepository) -> None:
    transition_srv = WorkflowTransitionService(repo)
    with pytest.raises(WorkflowNotFoundException):
        transition_srv.transition_stage(
            uuid4(),
            WorkflowStage.RESEARCH,
            ApprovalStatus.APPROVED,
            "reason",
        )


def test_workflow_history_service(repo: FakeWorkflowRepository) -> None:
    init = WorkflowInitializationService(repo)
    transition_srv = WorkflowTransitionService(repo)
    history_srv = WorkflowHistoryService(repo)
    project_id = uuid4()

    init.initialize_workflow(project_id)

    # 1st transition
    transition_srv.transition_stage(
        project_id=project_id,
        new_stage=WorkflowStage.RESEARCH,
        approval_status=ApprovalStatus.APPROVED,
        reason="R1",
    )

    # 2nd transition (RESEARCH -> IDEA)
    transition_srv.transition_stage(
        project_id=project_id,
        new_stage=WorkflowStage.IDEA,
        approval_status=ApprovalStatus.APPROVED,
        reason="R2",
    )

    history = history_srv.get_history(project_id)
    assert len(history) == 2
    assert history[0].new_stage == WorkflowStage.RESEARCH
    assert history[1].new_stage == WorkflowStage.IDEA


def test_workflow_history_service_not_found(repo: FakeWorkflowRepository) -> None:
    history_srv = WorkflowHistoryService(repo)
    with pytest.raises(WorkflowNotFoundException):
        history_srv.get_history(uuid4())
