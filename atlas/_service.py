"""The Atlas Platform facade.

This module provides the primary public interface for the Application Platform Layer.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from atlas.capabilities import (
    KnowledgeCapability,
    PresentationCapability,
    ProjectCapability,
    WorkflowCapability,
    WorkflowExecutionCapability,
)
from atlas.commands import (
    ApproveProposalCommand,
    ArchiveProjectCommand,
    Command,
    CreateProjectCommand,
    ExecuteStageCommand,
    GetWorkflowStatusCommand,
    ListProjectsCommand,
    LoadProjectCommand,
    RejectProposalCommand,
    ReviewKnowledgeCandidateCommand,
    TransitionStageCommand,
)
from atlas.contracts.envelope import RequestEnvelope, ResponseEnvelope
from atlas.contracts.errors import ErrorEnvelope, PlatformErrorCode, to_error_envelope
from atlas.exceptions import ApplicationError
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
from engine.ai.repository import ProposalRepository
from engine.architecture.repository import ArchitectureRepository
from engine.evaluation.repository import EvaluationRepository
from engine.knowledge.repository import KnowledgeRepository
from engine.planning.repository import PlanningRepository
from engine.project.services import (
    ProjectCreationService,
    ProjectLifecycleService,
    ProjectLoadingService,
    ProjectRegistryService,
)
from engine.research.repository import ResearchRepository
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

    Internally, each public method forwards to one of five capability
    objects (``atlas/capabilities/``) -- Project, Workflow, WorkflowExecution,
    Knowledge, Presentation -- each a thin, independently-testable delegation
    layer over the exact same Phase 1-14 services this facade always used.
    See docs/plans/phase-15-platform-layer.md for the full design.
    """

    def __init__(self, services: _AtlasServices) -> None:
        """Initialize the Atlas facade with required engine services."""
        self._project = ProjectCapability(
            project_creation_service=services.project_creation_service,
            project_loading_service=services.project_loading_service,
            project_listing_service=services.project_listing_service,
            project_archive_service=services.project_archive_service,
            workflow_initialization_service=services.workflow_initialization_service,
        )
        self._workflow = WorkflowCapability(
            workflow_repo=services.workflow_repo,
            workflow_transition_service=services.workflow_transition_service,
            orchestration_service=services.orchestration_service,
        )
        self._workflow_execution = WorkflowExecutionCapability(
            workflow_repo=services.workflow_repo,
            orchestration_service=services.orchestration_service,
            proposal_repo=services.proposal_repo,
        )
        self._knowledge = KnowledgeCapability(
            orchestration_service=services.orchestration_service,
        )
        self._presentation = PresentationCapability(
            project_loading_service=services.project_loading_service,
            workflow_repo=services.workflow_repo,
            orchestration_service=services.orchestration_service,
            research_repo=services.research_repo,
            planning_repo=services.planning_repo,
            architecture_repo=services.architecture_repo,
            evaluation_repo=services.evaluation_repo,
            knowledge_repo=services.knowledge_repo,
        )

        # Explicit, literal dispatch table for Atlas.handle() -- one entry per
        # existing Command subclass. No reflection, no getattr-by-name magic.
        self._dispatch: dict[type[Command], Any] = {
            CreateProjectCommand: self._project.create_project,
            LoadProjectCommand: self._project.load_project,
            ListProjectsCommand: self._project.list_projects,
            ArchiveProjectCommand: self._project.archive_project,
            GetWorkflowStatusCommand: self._workflow.get_workflow_status,
            TransitionStageCommand: self._workflow.transition_stage,
            ExecuteStageCommand: self._workflow_execution.execute_stage,
            ApproveProposalCommand: self._workflow_execution.approve_proposal,
            RejectProposalCommand: self._workflow_execution.reject_proposal,
            ReviewKnowledgeCandidateCommand: self._knowledge.review_knowledge_candidate,
        }

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
        self._presentation._bind(platform_orchestration, renderer_registry)

    def create_project(self, command: CreateProjectCommand) -> ProjectResult:
        """Initialize a new local engineering project."""
        return self._project.create_project(command)

    def load_project(self, command: LoadProjectCommand) -> ProjectResult:
        """Load an existing project by ID."""
        return self._project.load_project(command)

    def list_projects(self, command: ListProjectsCommand) -> ProjectListResult:
        """List all known projects."""
        return self._project.list_projects(command)

    def archive_project(self, command: ArchiveProjectCommand) -> OperationResult:
        """Archive a project."""
        return self._project.archive_project(command)

    def get_workflow_status(
        self, command: GetWorkflowStatusCommand
    ) -> WorkflowStatusResult:
        """Get current workflow state for a project."""
        return self._workflow.get_workflow_status(command)

    def transition_stage(self, command: TransitionStageCommand) -> WorkflowStatusResult:
        """Transition workflow to the next stage."""
        return self._workflow.transition_stage(command)

    def execute_stage(self, command: ExecuteStageCommand) -> ProposalResult:
        """Execute a workflow stage with AI generation."""
        return self._workflow_execution.execute_stage(command)

    def approve_proposal(self, command: ApproveProposalCommand) -> AppCommitResult:
        """Approve a generated AI proposal."""
        return self._workflow_execution.approve_proposal(command)

    def review_knowledge_candidate(
        self, command: ReviewKnowledgeCandidateCommand
    ) -> OperationResult:
        """Apply a human review decision to one pending knowledge candidate."""
        return self._knowledge.review_knowledge_candidate(command)

    def reject_proposal(self, command: RejectProposalCommand) -> OperationResult:
        """Reject a generated AI proposal with feedback."""
        return self._workflow_execution.reject_proposal(command)

    # -- Phase 15: uniform envelope dispatch --------------------------------
    #
    # The single doorway every out-of-process or protocol-driven client (MCP,
    # REST, IDE, AI/agent) is expected to call through. Named methods above
    # remain permanently supported for CLI, tests, internal tooling, and
    # direct SDK consumers -- see docs/plans/phase-15-platform-layer.md §4.2.

    def handle(self, envelope: RequestEnvelope[Any]) -> ResponseEnvelope[Any]:
        """Dispatch a versioned RequestEnvelope to the matching capability method."""
        handler = self._dispatch.get(type(envelope.command))
        if handler is None:
            error = ErrorEnvelope(
                code=PlatformErrorCode.UNKNOWN_ERROR,
                message=f"Unrecognized command type: {type(envelope.command).__name__}",
            )
            return ResponseEnvelope(request_id=envelope.request_id, error=error)
        try:
            result = handler(envelope.command)
            return ResponseEnvelope(request_id=envelope.request_id, result=result)
        except ApplicationError as exc:
            return ResponseEnvelope(
                request_id=envelope.request_id, error=to_error_envelope(exc)
            )

    # -- Phase 14: typed read models --------------------------------------
    #
    # These methods are the sole data source for presentation collectors.
    # Each returns an immutable DTO sourced from existing Phase 1-13
    # services/repositories. No engine entities or repositories are ever
    # exposed to callers.

    def get_project_read_model(self, project_id: UUID) -> ProjectReadModel:
        """Return the typed read model for a project's identity and status."""
        return self._presentation.get_project_read_model(project_id)

    def get_workflow_read_model(self, project_id: UUID) -> WorkflowReadModel:
        """Return the typed read model for a project's workflow state."""
        return self._presentation.get_workflow_read_model(project_id)

    def get_research_read_model(self, project_id: UUID) -> ResearchReadModel:
        """Return the typed read model for a project's research context."""
        return self._presentation.get_research_read_model(project_id)

    def get_knowledge_read_model(self, project_id: UUID) -> KnowledgeReadModel:
        """Return the typed read model for a project's engineering knowledge."""
        return self._presentation.get_knowledge_read_model(project_id)

    def get_diagnostics_read_model(self, project_id: UUID) -> DiagnosticsReadModel:
        """Return the typed read model summarizing subsystem health for a project."""
        return self._presentation.get_diagnostics_read_model(project_id)

    # -- Phase 14: presentation views and rendering -------------------------

    def get_project_dashboard_view(self, project_id: UUID) -> ProjectDashboardView:
        """Return the composed project dashboard view."""
        return self._presentation.get_project_dashboard_view(project_id)

    def get_workflow_status_view(self, project_id: UUID) -> WorkflowStatusView:
        """Return the composed workflow status view."""
        return self._presentation.get_workflow_status_view(project_id)

    def get_research_summary_view(self, project_id: UUID) -> ResearchSummaryView:
        """Return the composed research summary view."""
        return self._presentation.get_research_summary_view(project_id)

    def get_knowledge_summary_view(self, project_id: UUID) -> KnowledgeSummaryView:
        """Return the composed knowledge summary view."""
        return self._presentation.get_knowledge_summary_view(project_id)

    def get_diagnostics_view(self, project_id: UUID) -> DiagnosticsView:
        """Return the composed diagnostics view."""
        return self._presentation.get_diagnostics_view(project_id)

    def render(
        self,
        view: Any,
        renderer: str,
        contract: RenderContract | None = None,
    ) -> RenderResult:
        """Render an immutable presentation view using the named renderer."""
        return self._presentation.render(view, renderer, contract)
