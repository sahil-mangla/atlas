"""Offline composition root for tests, evals and examples.

Builds a real ``Atlas`` platform -- real repositories, services, validators
and commit path -- on a throwaway workspace, with the AI provider injected.
By default that provider is the deterministic ``ScriptedAIProvider``, so the
result needs no network access and no credentials.

Unlike the production bootstrap this wires no paper retrieval and no
semantic ranker, and reads no environment configuration.
"""

from pathlib import Path

from atlas_eng._service import Atlas, _AtlasServices
from atlas_eng.engine.ai.adapters.scripted import ScriptedAIProvider
from atlas_eng.engine.ai.context import IdentityContextStrategy
from atlas_eng.engine.ai.engineering_services import (
    ArchitectureAIEngineeringService,
    ArchitectureProposalTransformer,
    ArchitectureProposalValidator,
    EvaluationAIEngineeringService,
    EvaluationProposalTransformer,
    EvaluationProposalValidator,
    PlanningAIEngineeringService,
    PlanningProposalTransformer,
    PlanningProposalValidator,
    ProposalCommitService,
    ResearchAIEngineeringService,
    ResearchProposalTransformer,
    ResearchProposalValidator,
)
from atlas_eng.engine.ai.executor import PromptExecutor
from atlas_eng.engine.ai.fs_repository import FilesystemProposalRepository
from atlas_eng.engine.ai.provider import AIProvider
from atlas_eng.engine.ai.services import AIOrchestrationService, ContextAssemblerService
from atlas_eng.engine.architecture.fs_repository import FilesystemArchitectureRepository
from atlas_eng.engine.architecture.services import (
    ArchitecturalDecisionService,
    ArchitectureCompositionService,
    ArchitectureInitializationService,
    ArchitectureSummaryService,
    ComponentModelService,
    InterfaceContractService,
    RiskAnalysisService,
)
from atlas_eng.engine.domain.enums import WorkflowStage
from atlas_eng.engine.evaluation.fs_repository import FilesystemEvaluationRepository
from atlas_eng.engine.evaluation.services import (
    EvaluationInitializationService,
    EvaluationSummaryService,
    ReadinessEvaluationService,
)
from atlas_eng.engine.knowledge.extractors import (
    ArchitectureKnowledgeExtractor,
    EvaluationKnowledgeExtractor,
    ExtractorRegistry,
    PlanningKnowledgeExtractor,
    ResearchKnowledgeExtractor,
)
from atlas_eng.engine.knowledge.fs_repository import FilesystemKnowledgeRepository
from atlas_eng.engine.knowledge.orchestration import KnowledgeOrchestrationService
from atlas_eng.engine.knowledge.services import (
    KnowledgeApprovalService,
    KnowledgeCandidateService,
    KnowledgeDeduplicationService,
    KnowledgeLifecycleService,
    KnowledgeRetrievalService,
)
from atlas_eng.engine.memory.fs_repository import FilesystemMemoryRepository
from atlas_eng.engine.planning.fs_repository import FilesystemPlanningRepository
from atlas_eng.engine.planning.services import (
    MilestonePlanningService,
    PlanningInitializationService,
    PlanningSummaryService,
    ScopePlanningService,
    TaskPlanningService,
)
from atlas_eng.engine.project.fs_repository import FilesystemProjectRepository
from atlas_eng.engine.project.services import (
    ProjectCreationService,
    ProjectLifecycleService,
    ProjectLoadingService,
    ProjectRegistryService,
)
from atlas_eng.engine.prompt.loader import PromptLoader
from atlas_eng.engine.research.fs_repository import FilesystemResearchRepository
from atlas_eng.engine.research.services import (
    OpportunityAnalysisService,
    ResearchCaptureService,
    ResearchInitializationService,
    ResearchOrganizationService,
    ResearchSummaryService,
)
from atlas_eng.engine.workflow.fs_repository import FilesystemWorkflowRepository
from atlas_eng.engine.workflow.orchestration import (
    ArchitectureStageExecutor,
    EvaluationStageExecutor,
    PlanningStageExecutor,
    ResearchStageExecutor,
    StageServiceRegistry,
    WorkflowOrchestrationService,
)
from atlas_eng.engine.workflow.services import (
    WorkflowInitializationService,
    WorkflowProgressService,
    WorkflowReadinessService,
    WorkflowTransitionService,
)
from atlas_eng.observability.exporter import TraceExporter
from atlas_eng.presentation.collectors.collectors import (
    DiagnosticsCollector,
    KnowledgeSummaryCollector,
    ProjectDashboardCollector,
    ResearchSummaryCollector,
    WorkflowStatusCollector,
)
from atlas_eng.presentation.orchestration import PlatformOrchestrationService
from atlas_eng.presentation.renderers import RendererRegistry
from atlas_eng.presentation.renderers.base import (
    CliRenderer,
    JsonRenderer,
    MarkdownRenderer,
)


def create_test_platform(  # noqa: PLR0915
    tmp_path: Path,
    ai_provider: AIProvider | None = None,
    *,
    instrumentation_enabled: bool = True,
    exporter: TraceExporter | None = None,
) -> Atlas:
    """Construct the test platform using the production dependency shape.

    Args:
        tmp_path: Root temp directory for the test's workspace.
        ai_provider: Optional AI provider override. Defaults to a
            ``ScriptedAIProvider``, which returns a canned valid draft for
            every stage; set its ``stubbed_response`` between calls to drive
            one specific response through a real stage execution.
        instrumentation_enabled: Passed straight through to ``Atlas``.
        exporter: Passed straight through to ``Atlas``. Defaults (via
            ``Atlas`` itself) to ``NullExporter``, so existing callers see no
            behavior change and no filesystem side effects.
    """
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    project_repo = FilesystemProjectRepository(workspace_root)
    workflow_repo = FilesystemWorkflowRepository(project_repo)
    proposal_repo = FilesystemProposalRepository(project_repo)

    research_repo = FilesystemResearchRepository(project_repo)
    planning_repo = FilesystemPlanningRepository(project_repo)
    architecture_repo = FilesystemArchitectureRepository(project_repo)
    evaluation_repo = FilesystemEvaluationRepository(project_repo)
    memory_repo = FilesystemMemoryRepository(project_repo)
    knowledge_repo = FilesystemKnowledgeRepository(project_repo)
    context_assembler = ContextAssemblerService(
        research_repo=research_repo,
        planning_repo=planning_repo,
        architecture_repo=architecture_repo,
        evaluation_repo=evaluation_repo,
        memory_repo=memory_repo,
        project_repo=project_repo,
    )

    # Subsystem services used by the proposal transformers (mirrors _bootstrap.py).
    research_init = ResearchInitializationService(research_repo)
    research_capture = ResearchCaptureService(research_repo)
    research_org = ResearchOrganizationService(research_repo)
    opportunity_analysis = OpportunityAnalysisService(research_repo)
    research_summary = ResearchSummaryService(research_repo)
    planning_init = PlanningInitializationService(planning_repo, research_repo)
    scope_planning = ScopePlanningService(planning_repo)
    milestone_planning = MilestonePlanningService(planning_repo)
    task_planning = TaskPlanningService(planning_repo)
    planning_summary = PlanningSummaryService(planning_repo)
    architecture_init = ArchitectureInitializationService(
        project_repo, research_repo, planning_repo, architecture_repo
    )
    architecture_comp = ArchitectureCompositionService(
        architecture_repo, research_repo, planning_repo
    )
    architecture_summary = ArchitectureSummaryService(
        architecture_repo, research_repo, planning_repo
    )
    component_model = ComponentModelService(architecture_repo)
    adr_service = ArchitecturalDecisionService(
        architecture_repo, research_repo, planning_repo
    )
    interface_service = InterfaceContractService(architecture_repo)
    risk_service = RiskAnalysisService(architecture_repo)
    evaluation_init = EvaluationInitializationService(
        project_repo, research_repo, planning_repo, architecture_repo, evaluation_repo
    )
    evaluation_summary = EvaluationSummaryService(evaluation_repo)
    evaluation_readiness = ReadinessEvaluationService(evaluation_repo)

    prompt_registry = PromptLoader.load_registry()
    prompt_executor = PromptExecutor(
        ai_provider or ScriptedAIProvider(),
        IdentityContextStrategy(),
    )
    orchestrator = AIOrchestrationService(prompt_executor, prompt_registry)
    research_ai = ResearchAIEngineeringService(orchestrator, context_assembler)
    planning_ai = PlanningAIEngineeringService(orchestrator, context_assembler)
    architecture_ai = ArchitectureAIEngineeringService(orchestrator, context_assembler)
    evaluation_ai = EvaluationAIEngineeringService(orchestrator, context_assembler)

    research_transformer = ResearchProposalTransformer(
        research_repo,
        research_init,
        research_capture,
        research_org,
        opportunity_analysis,
        research_summary,
    )
    planning_transformer = PlanningProposalTransformer(
        planning_repo,
        research_repo,
        planning_init,
        scope_planning,
        milestone_planning,
        task_planning,
        planning_summary,
    )
    architecture_transformer = ArchitectureProposalTransformer(
        architecture_repo,
        research_repo,
        planning_repo,
        architecture_init,
        architecture_comp,
        architecture_summary,
        component_model,
        adr_service,
        interface_service,
        risk_service,
    )
    evaluation_transformer = EvaluationProposalTransformer(
        evaluation_repo,
        research_repo,
        planning_repo,
        architecture_repo,
        evaluation_init,
        evaluation_summary,
        evaluation_readiness,
    )
    commit_service = ProposalCommitService(
        research_repo,
        planning_repo,
        architecture_repo,
        evaluation_repo,
        research_transformer,
        planning_transformer,
        architecture_transformer,
        evaluation_transformer,
        ResearchProposalValidator(),
        PlanningProposalValidator(),
        ArchitectureProposalValidator(),
        EvaluationProposalValidator(),
    )

    registry = StageServiceRegistry(
        {
            WorkflowStage.RESEARCH: ResearchStageExecutor(research_ai),
            WorkflowStage.PLANNING: PlanningStageExecutor(planning_ai),
            WorkflowStage.ARCHITECTURE: ArchitectureStageExecutor(architecture_ai),
            WorkflowStage.REVIEW: EvaluationStageExecutor(evaluation_ai),
        }
    )
    workflow_initialization = WorkflowInitializationService(workflow_repo)
    workflow_transition = WorkflowTransitionService(workflow_repo)
    workflow_readiness = WorkflowReadinessService(workflow_repo)
    workflow_progress = WorkflowProgressService(workflow_repo)

    knowledge_lifecycle = KnowledgeLifecycleService(knowledge_repo)
    extractor_registry = ExtractorRegistry(
        ResearchKnowledgeExtractor(research_repo),
        PlanningKnowledgeExtractor(planning_repo),
        ArchitectureKnowledgeExtractor(architecture_repo),
        EvaluationKnowledgeExtractor(evaluation_repo),
    )
    knowledge_orchestration = KnowledgeOrchestrationService(
        KnowledgeCandidateService(knowledge_repo, KnowledgeDeduplicationService()),
        KnowledgeApprovalService(knowledge_repo, knowledge_lifecycle),
        KnowledgeRetrievalService(knowledge_repo),
        knowledge_lifecycle,
        extractor_registry,
    )

    project_archive_service = ProjectLifecycleService(project_repo)
    orchestration = WorkflowOrchestrationService(
        workflow_repo=workflow_repo,
        transition_service=workflow_transition,
        readiness_service=workflow_readiness,
        commit_service=commit_service,
        registry=registry,
        knowledge_orchestration=knowledge_orchestration,
        project_lifecycle_service=project_archive_service,
    )
    atlas = Atlas(
        _AtlasServices(
            project_creation_service=ProjectCreationService(project_repo),
            project_loading_service=ProjectLoadingService(project_repo),
            project_listing_service=ProjectRegistryService(project_repo),
            project_archive_service=project_archive_service,
            workflow_initialization_service=workflow_initialization,
            workflow_repo=workflow_repo,
            workflow_transition_service=workflow_transition,
            workflow_progress_service=workflow_progress,
            orchestration_service=orchestration,
            proposal_repo=proposal_repo,
            research_repo=research_repo,
            planning_repo=planning_repo,
            architecture_repo=architecture_repo,
            evaluation_repo=evaluation_repo,
            knowledge_repo=knowledge_repo,
        ),
        instrumentation_enabled=instrumentation_enabled,
        exporter=exporter,
    )

    platform_orchestration = PlatformOrchestrationService(
        project_dashboard=ProjectDashboardCollector(atlas),
        workflow_status=WorkflowStatusCollector(atlas),
        research_summary=ResearchSummaryCollector(atlas),
        knowledge_summary=KnowledgeSummaryCollector(atlas),
        diagnostics=DiagnosticsCollector(atlas),
    )
    renderer_registry = RendererRegistry(
        (JsonRenderer(), MarkdownRenderer(), CliRenderer())
    )
    atlas._bind_presentation(platform_orchestration, renderer_registry)

    return atlas
