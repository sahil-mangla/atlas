"""ATLAS Workflow Orchestration.

Composes existing AI engineering services, validators, and commit systems
into sequential pipeline executions.
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from engine.ai.engineering_services import (
    ArchitectureAIEngineeringService,
    EvaluationAIEngineeringService,
    PlanningAIEngineeringService,
    ProposalCommitService,
    ResearchAIEngineeringService,
)
from engine.domain.ai import AIProposal, ContextPayload
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
    KnowledgeSourceType,
    ProposalDecision,
    ProposalStatus,
    WorkflowStage,
)
from engine.domain.workflow import ProposalReviewEntry, Workflow
from engine.knowledge.orchestration import KnowledgeOrchestrationService
from engine.project.services import ProjectLifecycleService
from engine.workflow.exceptions import WorkflowException, WorkflowNotFoundException
from engine.workflow.repository import WorkflowRepository
from engine.workflow.services import (
    WorkflowReadinessService,
    WorkflowTransitionService,
)

# ==========================================
# Stage Executor Boundary
# ==========================================


class StageExecutor[T](ABC):
    """Encapsulates proposal generation and validation for a single stage."""

    @property
    @abstractmethod
    def stage(self) -> WorkflowStage:
        """The workflow stage this executor manages."""
        pass

    @abstractmethod
    def generate_proposal(
        self,
        project_id: UUID,
        user_instructions: str = "",
        context: ContextPayload | None = None,
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
        self,
        project_id: UUID,
        user_instructions: str = "",
        context: ContextPayload | None = None,
    ) -> AIProposal[ResearchProposalDraft]:
        return self.service.generate(project_id, user_instructions, context)


class PlanningStageExecutor(StageExecutor[PlanningProposalDraft]):
    def __init__(self, service: PlanningAIEngineeringService) -> None:
        self.service = service

    @property
    def stage(self) -> WorkflowStage:
        return WorkflowStage.PLANNING

    def generate_proposal(
        self,
        project_id: UUID,
        user_instructions: str = "",
        context: ContextPayload | None = None,
    ) -> AIProposal[PlanningProposalDraft]:
        return self.service.generate(project_id, user_instructions, context)


class ArchitectureStageExecutor(StageExecutor[ArchitectureProposalDraft]):
    def __init__(self, service: ArchitectureAIEngineeringService) -> None:
        self.service = service

    @property
    def stage(self) -> WorkflowStage:
        return WorkflowStage.ARCHITECTURE

    def generate_proposal(
        self,
        project_id: UUID,
        user_instructions: str = "",
        context: ContextPayload | None = None,
    ) -> AIProposal[ArchitectureProposalDraft]:
        return self.service.generate(project_id, user_instructions, context)


class EvaluationStageExecutor(StageExecutor[EvaluationProposalDraft]):
    def __init__(self, service: EvaluationAIEngineeringService) -> None:
        self.service = service

    @property
    def stage(self) -> WorkflowStage:
        return WorkflowStage.REVIEW

    def generate_proposal(
        self,
        project_id: UUID,
        user_instructions: str = "",
        context: ContextPayload | None = None,
    ) -> AIProposal[EvaluationProposalDraft]:
        return self.service.generate(project_id, user_instructions, context)


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

    def has_executor(self, stage: WorkflowStage) -> bool:
        """Report whether a stage has a registered AI proposal executor."""
        return stage in self._executors


# ==========================================
# Workflow Orchestration Service
# ==========================================


class WorkflowOrchestrationService:
    """Orchestrator driving complete AI-assisted engineering lifecycles.

    Coordinates generation, validation, readiness evaluation, and stage transition
    without maintaining any duplicate execution state.
    """

    def __init__(  # noqa: PLR0913
        self,
        workflow_repo: WorkflowRepository,
        transition_service: WorkflowTransitionService,
        readiness_service: WorkflowReadinessService,
        commit_service: ProposalCommitService,
        registry: StageServiceRegistry,
        knowledge_orchestration: KnowledgeOrchestrationService | None = None,
        project_lifecycle_service: ProjectLifecycleService | None = None,
    ) -> None:
        self.workflow_repo = workflow_repo
        self.transition_service = transition_service
        self.readiness_service = readiness_service
        self.commit_service = commit_service
        self.registry = registry
        self.knowledge_orchestration = knowledge_orchestration
        self.project_lifecycle_service = project_lifecycle_service

    def resolve_next_stage(self, workflow: Workflow) -> WorkflowStage:
        """Pick the next stage to transition to from ``workflow.pending_stages``.

        Skips ahead past any pending stage with no registered StageExecutor
        (e.g. PROBLEM_DEFINITION, IMPLEMENTATION) to the first one that has
        one, since those stages have nothing for ``stage execute`` to run.
        Falls back to the first pending stage if none of them have an
        executor (e.g. ITERATION/COMPLETION, which are legitimate
        executor-less terminal stages, not skip targets).
        """
        return next(
            (s for s in workflow.pending_stages if self.registry.has_executor(s)),
            workflow.pending_stages[0],
        )

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
        if not self.knowledge_orchestration:
            return executor.generate_proposal(project_id, user_instructions)
        knowledge = self.knowledge_orchestration.retrieve_for_stage(
            project_id, workflow.current_stage
        )
        service = getattr(executor, "service", None)
        context = None
        if service and hasattr(service, "context_assembler"):
            context = service.context_assembler.assemble_context(
                project_id, knowledge, stage=workflow.current_stage
            )
        return executor.generate_proposal(project_id, user_instructions, context)

    def process_knowledge_review(
        self,
        project_id: UUID,
        candidate_id: UUID,
        decision: ProposalDecision,
        actor: Any,
        feedback: str | None = None,
    ) -> Any:
        if not self.knowledge_orchestration:
            raise WorkflowException("Knowledge subsystem is not configured.")
        return self.knowledge_orchestration.process_candidate_review(
            project_id, candidate_id, decision, actor, feedback
        )

    def process_review_decision(  # noqa: PLR0913
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

        if decision == ProposalDecision.REJECT:
            workflow.record_proposal_review(
                ProposalReviewEntry(
                    proposal_id=proposal.id,
                    approver=review_approver,
                    decision=decision,
                    comment=review_comment,
                )
            )
            self.workflow_repo.save(workflow)
            proposal.status = ProposalStatus.REJECTED
            proposal.human_feedback = review_comment
            return None

        # 1. Proposal commit with deterministic rollback on failure.
        proposal.status = ProposalStatus.APPROVED
        commit_res = self.commit_service.commit_proposal(project_id, proposal)
        if not commit_res.success:
            return commit_res

        # Only record the review entry once the commit has actually succeeded,
        # so the audit trail in workflow.json never shows an approval that
        # wasn't durably committed.
        workflow.record_proposal_review(
            ProposalReviewEntry(
                proposal_id=proposal.id,
                approver=review_approver,
                decision=decision,
                comment=review_comment,
            )
        )

        # The stage's objectives are satisfied by its one required proposal
        # being committed -- clear them so readiness can actually pass.
        workflow.active_objectives = []
        self.workflow_repo.save(workflow)

        # Extract knowledge candidate post-commit
        if (
            commit_res.success
            and commit_res.committed_snapshot_id
            and self.knowledge_orchestration
        ):
            source_type = self._source_type_for_stage(workflow.current_stage)
            if source_type:
                self.knowledge_orchestration.extract_candidate_from_artifact(
                    project_id=project_id,
                    source_type=source_type,
                    source_id=commit_res.committed_snapshot_id,
                )

        # 2. Workflow Readiness Review
        readiness = self.readiness_service.evaluate_readiness(project_id)
        if readiness.status == EvaluationStatus.FAILED:
            return CommitResult(
                success=True,
                committed_snapshot_id=commit_res.committed_snapshot_id,
                transition_blocked=True,
                transition_errors=[
                    "Readiness review failed. "
                    f"Blocking issues: {readiness.blocking_issues}"
                ],
            )

        # 3. Workflow Transition (resolving target stage from workflow pending stages)
        if not workflow.pending_stages:
            # No next stage available, project completes sequence
            return commit_res

        target_stage = self.resolve_next_stage(workflow)
        try:
            self.transition_service.transition_stage(
                project_id=project_id,
                new_stage=target_stage,
                approval_status=ApprovalStatus.APPROVED,
                reason=transition_reason
                or f"Transitioning to {target_stage} after proposal commit.",
            )
        except Exception as e:
            return CommitResult(
                success=True,
                committed_snapshot_id=commit_res.committed_snapshot_id,
                transition_blocked=True,
                transition_errors=[f"Stage transition failed: {e}"],
            )

        if self.project_lifecycle_service:
            self.project_lifecycle_service.sync_workflow_state(project_id, target_stage)

        return commit_res

    def _source_type_for_stage(
        self, stage: WorkflowStage
    ) -> KnowledgeSourceType | None:
        return {
            WorkflowStage.RESEARCH: KnowledgeSourceType.RESEARCH_SNAPSHOT,
            WorkflowStage.PLANNING: KnowledgeSourceType.PLANNING_SNAPSHOT,
            WorkflowStage.ARCHITECTURE: KnowledgeSourceType.ARCHITECTURE_SNAPSHOT,
            WorkflowStage.REVIEW: KnowledgeSourceType.EVALUATION_SNAPSHOT,
        }.get(stage)
