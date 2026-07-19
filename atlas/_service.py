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
    ReviewKnowledgeCandidateCommand,
    TransitionStageCommand,
)
from atlas.exceptions import (
    AIProviderError,
    ApplicationError,
    BootstrapError,
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
from engine.architecture.repository import ArchitectureRepository
from engine.domain.ai import AIProposal
from engine.domain.ai_feedback import ProposalFeedback
from engine.domain.enums import (
    ApprovalStatus,
    KnowledgeCandidateStatus,
    ProposalDecision,
    PublishedKnowledgeStatus,
)
from engine.domain.enums import EvaluationStatus as EngineEvaluationStatus
from engine.evaluation.repository import EvaluationRepository
from engine.knowledge.exceptions import KnowledgeException
from engine.knowledge.repository import KnowledgeRepository
from engine.planning.repository import PlanningRepository
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
from engine.research.repository import ResearchRepository
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
from presentation.orchestration import PlatformOrchestrationService
from presentation.read_models import (
    DiagnosticsReadModel,
    KnowledgeReadModel,
    ProjectReadModel,
    ResearchReadModel,
    WorkflowReadModel,
)
from presentation.renderers import RenderContract, RendererRegistry, RenderResult
from presentation.views import (
    DiagnosticsView,
    KnowledgeSummaryView,
    ProjectDashboardView,
    ResearchSummaryView,
    WorkflowStatusView,
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
    # Read-only repositories backing the Phase 14 presentation read-model API.
    # Optional so existing test fixtures that don't exercise read models are
    # unaffected; the production bootstrap always supplies all of them.
    research_repo: ResearchRepository | None = None
    planning_repo: PlanningRepository | None = None
    architecture_repo: ArchitectureRepository | None = None
    evaluation_repo: EvaluationRepository | None = None
    knowledge_repo: KnowledgeRepository | None = None


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
        self._research_repo = services.research_repo
        self._planning_repo = services.planning_repo
        self._architecture_repo = services.architecture_repo
        self._evaluation_repo = services.evaluation_repo
        self._knowledge_repo = services.knowledge_repo

        # Proposal cache is bounded by removal after review completion.
        self._pending_proposals: dict[UUID, tuple[UUID, AIProposal[Any]]] = {}

        # Presentation wiring (PlatformOrchestrationService, RendererRegistry) is
        # attached by the composition root after this instance is constructed,
        # because the orchestration service's collectors require a live Atlas
        # reference. See atlas/_bootstrap.py and Atlas._bind_presentation.
        self._platform_orchestration: PlatformOrchestrationService | None = None
        self._renderer_registry: RendererRegistry | None = None

    def _bind_presentation(
        self,
        platform_orchestration: PlatformOrchestrationService,
        renderer_registry: RendererRegistry,
    ) -> None:
        """Attach presentation wiring built by the composition root.

        Internal hook. Only atlas/_bootstrap.py may call this, exactly once,
        during platform construction.
        """
        self._platform_orchestration = platform_orchestration
        self._renderer_registry = renderer_registry

    def _require_presentation(self) -> PlatformOrchestrationService:
        if self._platform_orchestration is None:
            raise BootstrapError(
                "Presentation layer is not configured on this Atlas instance."
            )
        return self._platform_orchestration

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
                pending_knowledge_candidates=[
                    candidate.id
                    for candidate in self._orchestration_service.knowledge_orchestration.list_pending_candidates(
                        command.project_id
                    )
                ]
                if self._orchestration_service.knowledge_orchestration
                else [],
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
                pending_knowledge_candidates=[
                    candidate.id
                    for candidate in self._orchestration_service.knowledge_orchestration.list_pending_candidates(
                        command.project_id
                    )
                ]
                if self._orchestration_service.knowledge_orchestration
                else [],
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

    def review_knowledge_candidate(
        self, command: ReviewKnowledgeCandidateCommand
    ) -> OperationResult:
        """Apply a human review decision to one pending knowledge candidate."""
        try:
            self._orchestration_service.process_knowledge_review(
                command.project_id,
                command.candidate_id,
                command.decision,
                command.actor,
                command.feedback,
            )
            return OperationResult(
                success=True, message="Knowledge candidate reviewed."
            )
        except (WorkflowException, KnowledgeException) as exc:
            raise ApplicationError(str(exc)) from exc

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

    # -- Phase 14: typed read models --------------------------------------
    #
    # These methods are the sole data source for presentation collectors.
    # Each returns an immutable DTO sourced from existing Phase 1-13
    # services/repositories. No engine entities or repositories are ever
    # exposed to callers.

    def get_project_read_model(self, project_id: UUID) -> ProjectReadModel:
        """Return the typed read model for a project's identity and status."""
        try:
            project = self._project_loading_service.load_project(project_id)
        except ProjectException as e:
            raise self._map_project_exception(e) from e
        return ProjectReadModel(
            id=project.id,
            name=project.name,
            description=project.description,
            objective=project.objective,
            status=project.status.value,
        )

    def get_workflow_read_model(self, project_id: UUID) -> WorkflowReadModel:
        """Return the typed read model for a project's workflow state."""
        workflow = self._workflow_repo.get_by_project_id(project_id)
        if not workflow:
            raise WorkflowNotReadyError(f"Workflow for project {project_id} not found.")
        readiness = self._orchestration_service.readiness_service.evaluate_readiness(
            project_id
        )
        knowledge_orchestration = self._orchestration_service.knowledge_orchestration
        pending_candidates = (
            tuple(
                candidate.id
                for candidate in knowledge_orchestration.list_pending_candidates(
                    project_id
                )
            )
            if knowledge_orchestration
            else ()
        )
        return WorkflowReadModel(
            project_id=project_id,
            current_stage=workflow.current_stage.value,
            readiness_status=readiness.status.value,
            is_ready=readiness.status != EngineEvaluationStatus.FAILED,
            objectives=tuple(workflow.active_objectives),
            blocking_issues=tuple(readiness.blocking_issues),
            pending_knowledge_candidates=pending_candidates,
        )

    def get_research_read_model(self, project_id: UUID) -> ResearchReadModel:
        """Return the typed read model for a project's research context."""
        if self._research_repo is None:
            raise BootstrapError("Research repository is not configured.")
        research = self._research_repo.get_by_project_id(project_id)
        if research is None:
            return ResearchReadModel(project_id=project_id, exists=False)
        latest_summary = (
            research.snapshots[-1].summary.synthesis if research.snapshots else ""
        )
        return ResearchReadModel(
            project_id=project_id,
            exists=True,
            source_count=len(research.sources),
            finding_count=len(research.findings),
            opportunity_count=len(research.opportunities),
            open_question_count=len(research.open_questions),
            latest_summary=latest_summary,
        )

    def get_knowledge_read_model(self, project_id: UUID) -> KnowledgeReadModel:
        """Return the typed read model for a project's engineering knowledge."""
        if self._knowledge_repo is None:
            raise BootstrapError("Knowledge repository is not configured.")
        candidates = self._knowledge_repo.list_candidates(project_id)
        pending_candidates = self._knowledge_repo.list_candidates(
            project_id, KnowledgeCandidateStatus.PENDING_REVIEW
        )
        published = self._knowledge_repo.list_published(project_id)
        active_published = self._knowledge_repo.list_published(
            project_id, PublishedKnowledgeStatus.ACTIVE
        )
        return KnowledgeReadModel(
            project_id=project_id,
            candidate_count=len(candidates),
            pending_candidate_count=len(pending_candidates),
            published_count=len(published),
            active_published_count=len(active_published),
            published_titles=tuple(entry.title for entry in active_published),
        )

    def get_diagnostics_read_model(self, project_id: UUID) -> DiagnosticsReadModel:
        """Return the typed read model summarizing subsystem health for a project."""
        try:
            self._project_loading_service.load_project(project_id)
        except ProjectException as e:
            raise self._map_project_exception(e) from e

        workflow_exists = self._workflow_repo.exists(project_id)
        research_exists = bool(
            self._research_repo and self._research_repo.exists(project_id)
        )
        planning_exists = bool(
            self._planning_repo and self._planning_repo.exists(project_id)
        )
        architecture_exists = bool(
            self._architecture_repo and self._architecture_repo.exists(project_id)
        )
        evaluation_exists = bool(
            self._evaluation_repo and self._evaluation_repo.exists(project_id)
        )
        knowledge_exists = bool(
            self._knowledge_repo
            and self._knowledge_repo.load_document(project_id) is not None
        )

        issues: list[str] = []
        if not workflow_exists:
            issues.append("Workflow not initialized.")
        if not research_exists:
            issues.append("Research not started.")
        if not planning_exists:
            issues.append("Planning not started.")
        if not architecture_exists:
            issues.append("Architecture not started.")
        if not evaluation_exists:
            issues.append("Evaluation not started.")

        return DiagnosticsReadModel(
            project_id=project_id,
            workflow_exists=workflow_exists,
            research_exists=research_exists,
            planning_exists=planning_exists,
            architecture_exists=architecture_exists,
            evaluation_exists=evaluation_exists,
            knowledge_exists=knowledge_exists,
            issues=tuple(issues),
        )

    # -- Phase 14: presentation views and rendering -------------------------

    def get_project_dashboard_view(self, project_id: UUID) -> ProjectDashboardView:
        """Return the composed project dashboard view."""
        return self._require_presentation().get_project_dashboard_view(project_id)

    def get_workflow_status_view(self, project_id: UUID) -> WorkflowStatusView:
        """Return the composed workflow status view."""
        return self._require_presentation().get_workflow_status_view(project_id)

    def get_research_summary_view(self, project_id: UUID) -> ResearchSummaryView:
        """Return the composed research summary view."""
        return self._require_presentation().get_research_summary_view(project_id)

    def get_knowledge_summary_view(self, project_id: UUID) -> KnowledgeSummaryView:
        """Return the composed knowledge summary view."""
        return self._require_presentation().get_knowledge_summary_view(project_id)

    def get_diagnostics_view(self, project_id: UUID) -> DiagnosticsView:
        """Return the composed diagnostics view."""
        return self._require_presentation().get_diagnostics_view(project_id)

    def render(
        self,
        view: Any,
        renderer: str,
        contract: RenderContract | None = None,
    ) -> RenderResult:
        """Render an immutable presentation view using the named renderer."""
        if self._renderer_registry is None:
            raise BootstrapError("Presentation renderers are not configured.")
        return self._renderer_registry.resolve(renderer).render(
            view, contract or RenderContract()
        )
