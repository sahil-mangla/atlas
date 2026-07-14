"""ATLAS Workflow Orchestration.

Composes existing AI engineering services, validators, and commit systems
into sequential pipeline executions.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

from engine.ai.engineering_services import (
    ArchitectureAIEngineeringService,
    EvaluationAIEngineeringService,
    PlanningAIEngineeringService,
    ProposalCommitService,
    ResearchAIEngineeringService,
)
from engine.domain.ai import AIProposal
from engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    CommitResult,
    EvaluationProposalDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
from engine.domain.ai_feedback import ProposalFeedback
from engine.domain.enums import (
    ApprovalStatus,
    EvaluationStatus,
    ProposalDecision,
    ProposalStatus,
    WorkflowStage,
)
from engine.domain.workflow import ProposalReviewEntry
from engine.workflow.exceptions import WorkflowException, WorkflowNotFoundException
from engine.workflow.repository import WorkflowRepository
from engine.workflow.services import (
    WorkflowReadinessService,
    WorkflowTransitionService,
)

T = TypeVar("T")


# ==========================================
# Stage Executor Boundary
# ==========================================

class StageExecutor(Generic[T], ABC):
    """Encapsulates proposal generation and validation for a single stage."""

    @property
    @abstractmethod
    def stage(self) -> WorkflowStage:
        """The workflow stage this executor manages."""
        pass

    @abstractmethod
    def generate_proposal(
        self, project_id: UUID, user_instructions: str = ""
    ) -> AIProposal[T]:
        """Trigger AI generation and validation, returning the typed proposal."""
        pass


class ResearchStageExecutor(StageExecutor[ResearchProposalDraft]):
    def __init__(self, service: ResearchAIEngineeringService) -> None:
        self.service = service

    @property
    def stage(self) -> WorkflowStage:
        return WorkflowStage.RESEARCH

    def generate_proposal(
        self, project_id: UUID, user_instructions: str = ""
    ) -> AIProposal[ResearchProposalDraft]:
        return self.service.generate(project_id, user_instructions)


class PlanningStageExecutor(StageExecutor[PlanningProposalDraft]):
    def __init__(self, service: PlanningAIEngineeringService) -> None:
        self.service = service

    @property
    def stage(self) -> WorkflowStage:
        return WorkflowStage.PLANNING

    def generate_proposal(
        self, project_id: UUID, user_instructions: str = ""
    ) -> AIProposal[PlanningProposalDraft]:
        return self.service.generate(project_id, user_instructions)


class ArchitectureStageExecutor(StageExecutor[ArchitectureProposalDraft]):
    def __init__(self, service: ArchitectureAIEngineeringService) -> None:
        self.service = service

    @property
    def stage(self) -> WorkflowStage:
        return WorkflowStage.ARCHITECTURE

    def generate_proposal(
        self, project_id: UUID, user_instructions: str = ""
    ) -> AIProposal[ArchitectureProposalDraft]:
        return self.service.generate(project_id, user_instructions)


class EvaluationStageExecutor(StageExecutor[EvaluationProposalDraft]):
    def __init__(self, service: EvaluationAIEngineeringService) -> None:
        self.service = service

    @property
    def stage(self) -> WorkflowStage:
        return WorkflowStage.REVIEW

    def generate_proposal(
        self, project_id: UUID, user_instructions: str = ""
    ) -> AIProposal[EvaluationProposalDraft]:
        return self.service.generate(project_id, user_instructions)


# ==========================================
# Immutable Service Registry
# ==========================================

class StageServiceRegistry:
    """Registry mapping WorkflowStages to their corresponding StageExecutors.

    Enforces immutability via constructor injection.
    """

    def __init__(self, executors: dict[WorkflowStage, StageExecutor[Any]]) -> None:
        """Initialize the immutable registry.

        Args:
            executors: Dictionary mapping WorkflowStage to StageExecutor.
        """
        self._executors = dict(executors)

    def get_executor(self, stage: WorkflowStage) -> StageExecutor[Any]:
        """Retrieve the executor for a workflow stage.

        Raises:
            WorkflowException: If no executor is registered for the stage.
        """
        executor = self._executors.get(stage)
        if not executor:
            raise WorkflowException(f"No StageExecutor registered for stage: {stage}")
        return executor


# ==========================================
# Workflow Orchestration Service
# ==========================================

class WorkflowOrchestrationService:
    """Orchestrator driving complete AI-assisted engineering lifecycles.

    Coordinates generation, validation, readiness evaluation, and stage transition
    without maintaining any duplicate execution state.
    """

    def __init__(
        self,
        workflow_repo: WorkflowRepository,
        transition_service: WorkflowTransitionService,
        readiness_service: WorkflowReadinessService,
        commit_service: ProposalCommitService,
        registry: StageServiceRegistry,
    ) -> None:
        self.workflow_repo = workflow_repo
        self.transition_service = transition_service
        self.readiness_service = readiness_service
        self.commit_service = commit_service
        self.registry = registry

    def generate_proposal(
        self, project_id: UUID, user_instructions: str = ""
    ) -> AIProposal[Any]:
        """Trigger generation for the active workflow stage.

        Args:
            project_id: The UUID of the project.
            user_instructions: Extra instructions passed to the prompt builder.
        """
        workflow = self.workflow_repo.get_by_project_id(project_id)
        if not workflow:
            raise WorkflowNotFoundException(
                f"Workflow for project {project_id} not found."
            )

        executor = self.registry.get_executor(workflow.current_stage)
        return executor.generate_proposal(project_id, user_instructions)

    def process_review_decision(
        self,
        project_id: UUID,
        proposal: AIProposal[Any],
        decision: ProposalDecision,
        feedback: ProposalFeedback | None = None,
        approver: str = "unknown",
        transition_reason: str = "",
    ) -> CommitResult | None:
        """Handle human review decisions.

        Enforces 'Proposal Commit' -> 'Readiness Review' -> 'Transition' flow.
        """
        workflow = self.workflow_repo.get_by_project_id(project_id)
        if not workflow:
            raise WorkflowNotFoundException(
                f"Workflow for project {project_id} not found."
            )

        review_comment = feedback.feedback if feedback else None
        review_approver = feedback.author if feedback else approver
        workflow.record_proposal_review(
            ProposalReviewEntry(
                proposal_id=proposal.id,
                approver=review_approver,
                decision=decision,
                comment=review_comment,
            )
        )
        self.workflow_repo.save(workflow)

        if decision == ProposalDecision.REJECT:
            proposal.status = ProposalStatus.REJECTED
            proposal.human_feedback = review_comment
            return None

        # 1. Proposal commit with deterministic rollback on failure.
        proposal.status = ProposalStatus.APPROVED
        commit_res = self.commit_service.commit_proposal(project_id, proposal)
        if not commit_res.success:
            return commit_res

        # 2. Workflow Readiness Review
        readiness = self.readiness_service.evaluate_readiness(project_id)
        if readiness.status == EvaluationStatus.FAILED:
            return CommitResult(
                success=True,
                committed_snapshot_id=commit_res.committed_snapshot_id,
                transition_blocked=True,
                transition_errors=[
                    f"Readiness review failed. Blocking issues: {readiness.blocking_issues}"
                ],
            )

        # 3. Workflow Transition (resolving target stage from workflow pending stages)
        if not workflow.pending_stages:
            # No next stage available, project completes sequence
            return commit_res

        target_stage = workflow.pending_stages[0]
        try:
            self.transition_service.transition_stage(
                project_id=project_id,
                new_stage=target_stage,
                approval_status=ApprovalStatus.APPROVED,
                reason=transition_reason or f"Transitioning to {target_stage} after proposal commit.",
            )
        except Exception as e:
            return CommitResult(
                success=True,
                committed_snapshot_id=commit_res.committed_snapshot_id,
                transition_blocked=True,
                transition_errors=[f"Stage transition failed: {e}"],
            )

        return commit_res
