"""Workflow status and transition capability.

Relocated verbatim from ``atlas/_service.py``'s pre-Phase-15 ``Atlas``
methods. This is a thin delegation layer -- see the Capability
Responsibility Rule in ``docs/plans/phase-15-platform-layer.md`` §3.5.
"""

from uuid import UUID

from atlas.commands import GetWorkflowStatusCommand, TransitionStageCommand
from atlas.exceptions import (
    ApplicationError,
    InvalidTransitionError,
    WorkflowNotReadyError,
)
from atlas.results import WorkflowStatusResult
from atlas.types import EvaluationStatus, WorkflowStage
from engine.domain.enums import ApprovalStatus
from engine.domain.enums import EvaluationStatus as EngineEvaluationStatus
from engine.project.services import ProjectLifecycleService
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowException,
    WorkflowNotFoundException,
)
from engine.workflow.orchestration import WorkflowOrchestrationService
from engine.workflow.repository import WorkflowRepository
from engine.workflow.services import WorkflowTransitionService


class WorkflowCapability:
    """Workflow status reporting and stage transitions."""

    def __init__(
        self,
        workflow_repo: WorkflowRepository,
        workflow_transition_service: WorkflowTransitionService,
        orchestration_service: WorkflowOrchestrationService,
        project_lifecycle_service: ProjectLifecycleService,
    ) -> None:
        self._workflow_repo = workflow_repo
        self._workflow_transition_service = workflow_transition_service
        self._orchestration_service = orchestration_service
        self._project_lifecycle_service = project_lifecycle_service

    def _map_workflow_exception(self, e: Exception) -> ApplicationError:
        """Map internal workflow exceptions to application errors."""
        if isinstance(e, WorkflowNotFoundException):
            return WorkflowNotReadyError(str(e))
        if isinstance(e, InvalidTransitionException):
            return InvalidTransitionError(str(e))
        if isinstance(e, WorkflowException):
            return ApplicationError(str(e))
        raise e

    def _pending_knowledge_candidate_ids(self, project_id: UUID) -> list[UUID]:
        knowledge_orchestration = self._orchestration_service.knowledge_orchestration
        if not knowledge_orchestration:
            return []
        candidates = knowledge_orchestration.list_pending_candidates(project_id)
        return [candidate.id for candidate in candidates]

    def get_workflow_status(
        self, command: GetWorkflowStatusCommand
    ) -> WorkflowStatusResult:
        """Get current workflow state for a project."""
        try:
            workflow = self._workflow_repo.get_by_project_id(command.project_id)
            if not workflow:
                raise WorkflowNotFoundException(
                    f"Workflow for project {command.project_id} not found."
                )
            readiness = (
                self._orchestration_service.readiness_service.evaluate_readiness(
                    command.project_id
                )
            )
            return WorkflowStatusResult(
                project_id=command.project_id,
                current_stage=WorkflowStage(workflow.current_stage.value),
                objectives=workflow.active_objectives,
                is_ready_for_transition=readiness.status
                != EngineEvaluationStatus.FAILED,
                readiness_status=EvaluationStatus(readiness.status.value),
                blocking_issues=readiness.blocking_issues,
                pending_knowledge_candidates=self._pending_knowledge_candidate_ids(
                    command.project_id
                ),
            )
        except WorkflowException as e:
            raise self._map_workflow_exception(e) from e

    def transition_stage(self, command: TransitionStageCommand) -> WorkflowStatusResult:
        """Transition workflow to the next stage."""
        try:
            workflow = self._workflow_repo.get_by_project_id(command.project_id)
            if not workflow:
                raise WorkflowNotFoundException(
                    f"Workflow for project {command.project_id} not found."
                )
            if not workflow.pending_stages:
                raise InvalidTransitionException("No pending stages available.")

            target_stage = workflow.pending_stages[0]
            self._workflow_transition_service.transition_stage(
                project_id=command.project_id,
                new_stage=target_stage,
                approval_status=ApprovalStatus.APPROVED,
                reason=command.reason or "Requested by client adapter.",
            )
            self._project_lifecycle_service.sync_workflow_state(
                command.project_id, target_stage
            )

            # Reload workflow to get updated status
            workflow = self._workflow_repo.get_by_project_id(command.project_id)
            if not workflow:
                raise WorkflowNotFoundException(
                    f"Workflow for project {command.project_id} not found."
                )
            readiness = (
                self._orchestration_service.readiness_service.evaluate_readiness(
                    command.project_id
                )
            )

            return WorkflowStatusResult(
                project_id=command.project_id,
                current_stage=WorkflowStage(workflow.current_stage.value),
                objectives=workflow.active_objectives,
                is_ready_for_transition=readiness.status
                != EngineEvaluationStatus.FAILED,
                readiness_status=EvaluationStatus(readiness.status.value),
                blocking_issues=readiness.blocking_issues,
                pending_knowledge_candidates=self._pending_knowledge_candidate_ids(
                    command.project_id
                ),
            )
        except WorkflowException as e:
            raise self._map_workflow_exception(e) from e
