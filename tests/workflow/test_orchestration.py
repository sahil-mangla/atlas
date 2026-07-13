from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from engine.ai.exceptions import InvalidProposalException
from engine.ai.engineering_services import ProposalCommitService
from engine.domain.ai import AIProposal, ContextPayload, PromptTemplateMetadata
from engine.domain.ai_drafts import CommitResult, ResearchProposalDraft
from engine.domain.ai_feedback import ProposalFeedback
from engine.domain.enums import (
    ApprovalStatus,
    EvaluationStatus,
    ProposalDecision,
    ProposalStatus,
    ProposalType,
    WorkflowStage,
)
from engine.domain.workflow import Workflow
from engine.workflow.exceptions import WorkflowException, WorkflowNotFoundException
from engine.workflow.orchestration import (
    ResearchStageExecutor,
    StageExecutor,
    StageServiceRegistry,
    WorkflowOrchestrationService,
)
from engine.workflow.repository import WorkflowRepository
from engine.workflow.services import (
    WorkflowReadinessService,
    WorkflowTransitionService,
)


class DummyWorkflowRepo(WorkflowRepository):
    def __init__(self) -> None:
        self.workflow: Any = None

    def get_by_project_id(self, project_id: UUID) -> Any:
        return self.workflow

    def save(self, workflow: Any) -> None:
        self.workflow = workflow

    def exists(self, project_id: UUID) -> bool:
        return self.workflow is not None

    def get_by_id(self, workflow_id: UUID) -> Any:
        return None

    def discover(self) -> list[Any]:
        return []


def test_registry_immutability() -> None:
    executor = Mock(spec=StageExecutor)
    registry = StageServiceRegistry({WorkflowStage.RESEARCH: executor})
    
    assert registry.get_executor(WorkflowStage.RESEARCH) is executor
    with pytest.raises(WorkflowException):
        registry.get_executor(WorkflowStage.PLANNING)


def test_generate_proposal_delegation() -> None:
    workflow_repo = DummyWorkflowRepo()
    project_id = uuid4()
    
    mock_workflow = Mock(spec=Workflow)
    mock_workflow.current_stage = WorkflowStage.RESEARCH
    workflow_repo.workflow = mock_workflow

    executor = Mock(spec=StageExecutor)
    proposal = AIProposal[ResearchProposalDraft](
        proposal_type=ProposalType.RESEARCH,
        status=ProposalStatus.DRAFT,
        prompt_metadata=PromptTemplateMetadata(version=1, supported_subsystem=ProposalType.RESEARCH),
        context_used=ContextPayload(serialized_context=""),
        data=ResearchProposalDraft(problem_statement="Test", objectives=[]),
    )
    executor.generate_proposal.return_value = proposal
    
    registry = StageServiceRegistry({WorkflowStage.RESEARCH: executor})
    
    service = WorkflowOrchestrationService(
        workflow_repo=workflow_repo,
        transition_service=Mock(),
        readiness_service=Mock(),
        commit_service=Mock(),
        registry=registry,
    )
    
    res = service.generate_proposal(project_id, "Test instr")
    assert res is proposal
    executor.generate_proposal.assert_called_once_with(project_id, "Test instr")


def test_process_rejection_flow() -> None:
    workflow_repo = DummyWorkflowRepo()
    project_id = uuid4()
    mock_workflow = Mock(spec=Workflow)
    mock_workflow.current_stage = WorkflowStage.RESEARCH
    workflow_repo.workflow = mock_workflow

    executor = Mock(spec=StageExecutor)
    registry = StageServiceRegistry({WorkflowStage.RESEARCH: executor})

    commit_service = Mock(spec=ProposalCommitService)
    service = WorkflowOrchestrationService(
        workflow_repo=workflow_repo,
        transition_service=Mock(),
        readiness_service=Mock(),
        commit_service=commit_service,
        registry=registry,
    )

    proposal = AIProposal[ResearchProposalDraft](
        proposal_type=ProposalType.RESEARCH,
        status=ProposalStatus.PENDING_REVIEW,
        prompt_metadata=PromptTemplateMetadata(version=1, supported_subsystem=ProposalType.RESEARCH),
        context_used=ContextPayload(serialized_context=""),
        data=ResearchProposalDraft(problem_statement="Test", objectives=[]),
    )

    feedback = ProposalFeedback(
        proposal_id=proposal.id,
        author="human",
        feedback="Objective is too vague",
    )

    res = service.process_review_decision(
        project_id=project_id,
        proposal=proposal,
        decision=ProposalDecision.REJECT,
        feedback=feedback,
    )

    assert res is None
    assert proposal.status == ProposalStatus.REJECTED
    assert proposal.human_feedback == "Objective is too vague"
    commit_service.commit_proposal.assert_not_called()
    assert mock_workflow.record_proposal_review.call_count == 1


def test_process_approval_readiness_block() -> None:
    workflow_repo = DummyWorkflowRepo()
    project_id = uuid4()
    mock_workflow = Mock(spec=Workflow)
    mock_workflow.current_stage = WorkflowStage.RESEARCH
    workflow_repo.workflow = mock_workflow

    executor = Mock(spec=StageExecutor)
    registry = StageServiceRegistry({WorkflowStage.RESEARCH: executor})

    commit_service = Mock(spec=ProposalCommitService)
    commit_service.commit_proposal.return_value = CommitResult(success=True)

    readiness_service = Mock(spec=WorkflowReadinessService)
    mock_review = Mock()
    mock_review.status = EvaluationStatus.FAILED
    mock_review.blocking_issues = ["Complete the paper references"]
    readiness_service.evaluate_readiness.return_value = mock_review

    service = WorkflowOrchestrationService(
        workflow_repo=workflow_repo,
        transition_service=Mock(),
        readiness_service=readiness_service,
        commit_service=commit_service,
        registry=registry,
    )

    proposal = AIProposal[ResearchProposalDraft](
        proposal_type=ProposalType.RESEARCH,
        status=ProposalStatus.PENDING_REVIEW,
        prompt_metadata=PromptTemplateMetadata(version=1, supported_subsystem=ProposalType.RESEARCH),
        context_used=ContextPayload(serialized_context=""),
        data=ResearchProposalDraft(problem_statement="Test", objectives=[]),
    )

    res = service.process_review_decision(
        project_id=project_id,
        proposal=proposal,
        decision=ProposalDecision.APPROVE,
    )

    assert res is not None
    assert res.success
    assert res.transition_blocked
    assert "Readiness review failed" in res.transition_errors[0]
    commit_service.commit_proposal.assert_called_once_with(project_id, proposal)


def test_process_approval_success_transition() -> None:
    workflow_repo = DummyWorkflowRepo()
    project_id = uuid4()
    mock_workflow = Mock(spec=Workflow)
    mock_workflow.current_stage = WorkflowStage.RESEARCH
    mock_workflow.pending_stages = [WorkflowStage.PLANNING]
    workflow_repo.workflow = mock_workflow

    executor = Mock(spec=StageExecutor)
    registry = StageServiceRegistry({WorkflowStage.RESEARCH: executor})

    commit_service = Mock(spec=ProposalCommitService)
    commit_service.commit_proposal.return_value = CommitResult(
        success=True, committed_snapshot_id=uuid4()
    )

    readiness_service = Mock(spec=WorkflowReadinessService)
    mock_review = Mock()
    mock_review.status = EvaluationStatus.PASSED
    readiness_service.evaluate_readiness.return_value = mock_review

    transition_service = Mock(spec=WorkflowTransitionService)

    service = WorkflowOrchestrationService(
        workflow_repo=workflow_repo,
        transition_service=transition_service,
        readiness_service=readiness_service,
        commit_service=commit_service,
        registry=registry,
    )

    proposal = AIProposal[ResearchProposalDraft](
        proposal_type=ProposalType.RESEARCH,
        status=ProposalStatus.PENDING_REVIEW,
        prompt_metadata=PromptTemplateMetadata(version=1, supported_subsystem=ProposalType.RESEARCH),
        context_used=ContextPayload(serialized_context=""),
        data=ResearchProposalDraft(problem_statement="Test", objectives=[]),
    )

    res = service.process_review_decision(
        project_id=project_id,
        proposal=proposal,
        decision=ProposalDecision.APPROVE,
        transition_reason="All verified",
    )

    assert res is not None
    assert res.success
    assert proposal.status == ProposalStatus.APPROVED
    
    commit_service.commit_proposal.assert_called_once_with(project_id, proposal)
    readiness_service.evaluate_readiness.assert_called_once_with(project_id)
    transition_service.transition_stage.assert_called_once_with(
        project_id=project_id,
        new_stage=WorkflowStage.PLANNING,
        approval_status=ApprovalStatus.APPROVED,
        reason="All verified",
    )
