"""The Atlas Platform facade.

This module provides the primary public interface for the Application Platform Layer.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from atlas.commands import (
    ApproveProposalCommand,
    ArchiveProjectCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    GetWorkflowStatusCommand,
    ListProjectsCommand,
    LoadProjectCommand,
    RejectProposalCommand,
    TransitionStageCommand,
)
from atlas.exceptions import (
    AIProviderError,
    ApplicationError,
    ContextAssemblyError,
    InvalidProjectError,
    InvalidTransitionError,
    ProjectAlreadyExistsError,
    ProjectLifecycleError,
    ProjectNotFoundError,
    ProposalValidationError,
    StageExecutionError,
    WorkflowNotReadyError,
)
from atlas.results import (
    CommitResult as AppCommitResult,
)
from atlas.results import (
    OperationResult,
    ProjectListResult,
    ProjectResult,
    ProposalResult,
    WorkflowStatusResult,
)
from atlas.types import EvaluationStatus, ProjectStatus, ProposalStatus, WorkflowStage
from engine.ai.exceptions import (
    AIException,
    AIProviderException,
    InvalidContextException,
    InvalidProposalException,
)
from engine.ai.repository import ProposalRepository
from engine.domain.ai import AIProposal
from engine.domain.ai_feedback import ProposalFeedback
from engine.domain.enums import ApprovalStatus, ProposalDecision
from engine.domain.enums import EvaluationStatus as EngineEvaluationStatus
from engine.project.exceptions import (
    InvalidProjectException,
    ProjectAlreadyExistsException,
    ProjectException,
    ProjectLifecycleException,
    ProjectNotFoundException,
)
from engine.project.services import (
    ProjectCreationService,
    ProjectLifecycleService,
    ProjectLoadingService,
    ProjectRegistryService,
)
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowException,
    WorkflowNotFoundException,
)
from engine.workflow.orchestration import WorkflowOrchestrationService
from engine.workflow.repository import WorkflowRepository
from engine.workflow.services import (
    WorkflowInitializationService,
    WorkflowTransitionService,
)


@dataclass(frozen=True)
class _AtlasServices:
    """Internal dependency container for the public Atlas façade."""

    project_creation_service: ProjectCreationService
    project_loading_service: ProjectLoadingService
    project_listing_service: ProjectRegistryService
    project_archive_service: ProjectLifecycleService
    workflow_initialization_service: WorkflowInitializationService
    workflow_repo: WorkflowRepository
    workflow_transition_service: WorkflowTransitionService
    orchestration_service: WorkflowOrchestrationService
    proposal_repo: ProposalRepository


class Atlas:
    """The canonical public interface for the ATLAS engineering platform.

    Accepts Commands, delegates to internal engine services, and returns Results.
    """

    def __init__(self, services: _AtlasServices) -> None:
        """Initialize the Atlas facade with required engine services."""
        self._project_creation_service = services.project_creation_service
        self._project_loading_service = services.project_loading_service
        self._project_listing_service = services.project_listing_service
        self._project_archive_service = services.project_archive_service
        self._workflow_initialization_service = services.workflow_initialization_service
        self._workflow_repo = services.workflow_repo
        self._workflow_transition_service = services.workflow_transition_service
        self._orchestration_service = services.orchestration_service
        self._proposal_repo = services.proposal_repo

        # Proposal cache is bounded by removal after review completion.
        self._pending_proposals: dict[UUID, tuple[UUID, AIProposal[Any]]] = {}

    def _map_project_exception(self, e: Exception) -> ApplicationError:
        """Map internal project exceptions to application errors."""
        if isinstance(e, ProjectNotFoundException):
            return ProjectNotFoundError(str(e))
        if isinstance(e, ProjectAlreadyExistsException):
            return ProjectAlreadyExistsError(str(e))
        if isinstance(e, InvalidProjectException):
            return InvalidProjectError(str(e))
        if isinstance(e, ProjectLifecycleException):
            return ProjectLifecycleError(str(e))
        if isinstance(e, ProjectException):
            return ApplicationError(str(e))
        raise e

    def _map_workflow_exception(self, e: Exception) -> ApplicationError:
        """Map internal workflow exceptions to application errors."""
        if isinstance(e, WorkflowNotFoundException):
            return WorkflowNotReadyError(str(e))
        if isinstance(e, InvalidTransitionException):
            return InvalidTransitionError(str(e))
        if isinstance(e, WorkflowException):
            return ApplicationError(str(e))
        raise e

    def _map_ai_exception(self, e: Exception) -> ApplicationError:
        """Map internal AI exceptions to application errors."""
        if isinstance(e, AIProviderException):
            return AIProviderError(str(e))
        if isinstance(e, InvalidContextException):
            return ContextAssemblyError(str(e))
        if isinstance(e, InvalidProposalException):
            return ProposalValidationError(str(e))
        if isinstance(e, AIException):
            return StageExecutionError(str(e))
        raise e

    def create_project(self, command: CreateProjectCommand) -> ProjectResult:
        """Initialize a new local engineering project."""
        try:
            project = self._project_creation_service.create_project(
                name=command.name,
                description=command.description,
                objective=command.objective,
                path=Path(command.path) if command.path else None,
            )
            self._workflow_initialization_service.initialize_workflow(project.id)
            return ProjectResult(
                id=project.id,
                name=project.name,
                description=project.description,
                objective=project.objective,
                status=ProjectStatus(project.status.value),
            )
        except ProjectException as e:
            raise self._map_project_exception(e) from e

    def load_project(self, command: LoadProjectCommand) -> ProjectResult:
        """Load an existing project by ID."""
        try:
            project = self._project_loading_service.load_project(command.project_id)
            return ProjectResult(
                id=project.id,
                name=project.name,
                description=project.description,
                objective=project.objective,
                status=ProjectStatus(project.status.value),
            )
        except ProjectException as e:
            raise self._map_project_exception(e) from e

    def list_projects(self, _command: ListProjectsCommand) -> ProjectListResult:
        """List all known projects."""
        try:
            projects = self._project_listing_service.list_projects()
            results = [
                ProjectResult(
                    id=p.id,
                    name=p.name,
                    description=p.description,
                    objective=p.objective,
                    status=ProjectStatus(p.status.value),
                )
                for p in projects
            ]
            return ProjectListResult(projects=results)
        except ProjectException as e:
            raise self._map_project_exception(e) from e

    def archive_project(self, command: ArchiveProjectCommand) -> OperationResult:
        """Archive a project."""
        try:
            self._project_archive_service.archive_project(command.project_id)
            return OperationResult(
                success=True, message="Project archived successfully."
            )
        except ProjectException as e:
            raise self._map_project_exception(e) from e

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
            )
        except WorkflowException as e:
            raise self._map_workflow_exception(e) from e

    def execute_stage(self, command: ExecuteStageCommand) -> ProposalResult:
        """Execute a workflow stage with AI generation."""
        try:
            workflow = self._workflow_repo.get_by_project_id(command.project_id)
            if not workflow:
                raise WorkflowNotFoundException(
                    f"Workflow for project {command.project_id} not found."
                )
            if workflow.current_stage.value != command.stage.value:
                raise InvalidTransitionError(
                    "Requested stage does not match the active workflow stage."
                )
            proposal = self._orchestration_service.generate_proposal(
                project_id=command.project_id, user_instructions=""
            )
            self._proposal_repo.save(command.project_id, proposal)
            self._pending_proposals[proposal.id] = (command.project_id, proposal)
            return ProposalResult(
                id=proposal.id,
                project_id=command.project_id,
                stage=command.stage,
                status=ProposalStatus(proposal.status.value),
                content=proposal.data.model_dump()
                if hasattr(proposal.data, "model_dump")
                else proposal.data,
            )
        except AIException as e:
            raise self._map_ai_exception(e) from e
        except WorkflowException as e:
            raise self._map_workflow_exception(e) from e

    def approve_proposal(self, command: ApproveProposalCommand) -> AppCommitResult:
        """Approve a generated AI proposal."""
        record = self._pending_proposals.get(command.proposal_id)
        if not record:
            record = self._proposal_repo.get_by_id(command.proposal_id)
        if not record:
            raise ProposalValidationError(
                f"Proposal {command.proposal_id} not found or expired."
            )
        proposal_project_id, proposal = record
        if proposal_project_id != command.project_id:
            raise ProposalValidationError(
                "Proposal does not belong to the requested project."
            )

        try:
            commit_res = self._orchestration_service.process_review_decision(
                project_id=command.project_id,
                proposal=proposal,
                decision=ProposalDecision.APPROVE,
                approver=command.actor,
            )
            if commit_res:
                result = AppCommitResult(
                    success=commit_res.success,
                    proposal_id=command.proposal_id,
                    patch_summary=(
                        f"Snapshot {commit_res.committed_snapshot_id} committed."
                    ),
                )
                if result.success:
                    self._pending_proposals.pop(command.proposal_id, None)
                    self._proposal_repo.delete(command.proposal_id)
                return result
            return AppCommitResult(
                success=False,
                proposal_id=command.proposal_id,
                patch_summary="Commit failed.",
            )
        except AIException as e:
            raise self._map_ai_exception(e) from e
        except WorkflowException as e:
            raise self._map_workflow_exception(e) from e

    def reject_proposal(self, command: RejectProposalCommand) -> OperationResult:
        """Reject a generated AI proposal with feedback."""
        record = self._pending_proposals.get(command.proposal_id)
        if not record:
            record = self._proposal_repo.get_by_id(command.proposal_id)
        if not record:
            raise ProposalValidationError(
                f"Proposal {command.proposal_id} not found or expired."
            )
        proposal_project_id, proposal = record
        if proposal_project_id != command.project_id:
            raise ProposalValidationError(
                "Proposal does not belong to the requested project."
            )

        try:
            feedback = ProposalFeedback(
                feedback=command.feedback,
                proposal_id=command.proposal_id,
                author=command.actor,
            )
            self._orchestration_service.process_review_decision(
                project_id=command.project_id,
                proposal=proposal,
                decision=ProposalDecision.REJECT,
                feedback=feedback,
                approver="Client Adapter",
            )
            self._pending_proposals.pop(command.proposal_id, None)
            self._proposal_repo.delete(command.proposal_id)
            return OperationResult(success=True, message="Proposal rejected.")
        except AIException as e:
            raise self._map_ai_exception(e) from e
        except WorkflowException as e:
            raise self._map_workflow_exception(e) from e
