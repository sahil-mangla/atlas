"""Typed read models, composed views, and rendering capability.

Relocated verbatim from ``atlas/_service.py``'s pre-Phase-15 ``Atlas``
methods (the "Phase 14: typed read models" and "Phase 14: presentation
views and rendering" sections). This is a thin delegation layer -- see the
Capability Responsibility Rule in ``docs/plans/phase-15-platform-layer.md``
§3.5.

This is the one capability requiring the deferred-attach pattern: its
constructor takes only the read-model repositories (available immediately
at ``Atlas.__init__`` time), while ``PlatformOrchestrationService`` and
``RendererRegistry`` are attached later via ``_bind``, preserving the exact
two-phase composition-root contract documented in
``docs/architecture/presentation-layer.md``.
"""

from typing import Any
from uuid import UUID

from atlas.exceptions import (
    ApplicationError,
    BootstrapError,
    InvalidProjectError,
    ProjectAlreadyExistsError,
    ProjectLifecycleError,
    ProjectNotFoundError,
    WorkflowNotReadyError,
)
from engine.architecture.repository import ArchitectureRepository
from engine.domain.enums import EvaluationStatus as EngineEvaluationStatus
from engine.domain.enums import KnowledgeCandidateStatus, PublishedKnowledgeStatus
from engine.evaluation.repository import EvaluationRepository
from engine.knowledge.repository import KnowledgeRepository
from engine.planning.repository import PlanningRepository
from engine.project.exceptions import (
    InvalidProjectException,
    ProjectAlreadyExistsException,
    ProjectException,
    ProjectLifecycleException,
    ProjectNotFoundException,
)
from engine.project.services import ProjectLoadingService
from engine.research.repository import ResearchRepository
from engine.workflow.orchestration import WorkflowOrchestrationService
from engine.workflow.repository import WorkflowRepository
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


class PresentationCapability:
    """Typed read models, composed presentation views, and rendering."""

    def __init__(  # noqa: PLR0913
        self,
        project_loading_service: ProjectLoadingService,
        workflow_repo: WorkflowRepository,
        orchestration_service: WorkflowOrchestrationService,
        research_repo: ResearchRepository | None,
        planning_repo: PlanningRepository | None,
        architecture_repo: ArchitectureRepository | None,
        evaluation_repo: EvaluationRepository | None,
        knowledge_repo: KnowledgeRepository | None,
    ) -> None:
        self._project_loading_service = project_loading_service
        self._workflow_repo = workflow_repo
        self._orchestration_service = orchestration_service
        self._research_repo = research_repo
        self._planning_repo = planning_repo
        self._architecture_repo = architecture_repo
        self._evaluation_repo = evaluation_repo
        self._knowledge_repo = knowledge_repo

        # Presentation wiring (PlatformOrchestrationService, RendererRegistry) is
        # attached by the composition root via _bind() after this instance is
        # constructed -- see docs/architecture/presentation-layer.md.
        self._platform_orchestration: PlatformOrchestrationService | None = None
        self._renderer_registry: RendererRegistry | None = None

    def _map_project_exception(self, e: Exception) -> ApplicationError:
        """Map internal project exceptions to application errors.

        Duplicated from ProjectCapability rather than shared, so this
        capability never depends on another capability's instance -- see
        the "no cross-capability coupling" dependency rule (§3.2 of the
        Phase 15 plan).
        """
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

    def _bind(
        self,
        platform_orchestration: PlatformOrchestrationService,
        renderer_registry: RendererRegistry,
    ) -> None:
        """Attach presentation wiring built by the composition root.

        Internal hook. Only atlas/_bootstrap.py (via Atlas._bind_presentation)
        may call this, exactly once, during platform construction.
        """
        self._platform_orchestration = platform_orchestration
        self._renderer_registry = renderer_registry

    def _require_presentation(self) -> PlatformOrchestrationService:
        if self._platform_orchestration is None:
            raise BootstrapError(
                "Presentation layer is not configured on this Atlas instance."
            )
        return self._platform_orchestration

    # -- Phase 14: typed read models --------------------------------------

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
