"""Test composition root for the public Atlas SDK."""

from pathlib import Path

from atlas._service import Atlas, _AtlasServices
from engine.ai.context import IdentityContextStrategy
from engine.ai.engineering_services import (
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
from engine.ai.executor import PromptExecutor
from engine.ai.fs_repository import FilesystemProposalRepository
from engine.ai.provider import AIProvider
from engine.ai.services import AIOrchestrationService, ContextAssemblerService
from engine.architecture.fs_repository import FilesystemArchitectureRepository
from engine.architecture.services import (
    ArchitecturalDecisionService,
    ArchitectureCompositionService,
    ArchitectureInitializationService,
    ArchitectureSummaryService,
    ComponentModelService,
    InterfaceContractService,
    RiskAnalysisService,
)
from engine.domain.enums import WorkflowStage
from engine.evaluation.fs_repository import FilesystemEvaluationRepository
from engine.evaluation.services import (
    EvaluationInitializationService,
    EvaluationSummaryService,
    ReadinessEvaluationService,
)
from engine.knowledge.extractors import (
    ArchitectureKnowledgeExtractor,
    EvaluationKnowledgeExtractor,
    ExtractorRegistry,
    PlanningKnowledgeExtractor,
    ResearchKnowledgeExtractor,
)
from engine.knowledge.fs_repository import FilesystemKnowledgeRepository
from engine.knowledge.orchestration import KnowledgeOrchestrationService
from engine.knowledge.services import (
    KnowledgeApprovalService,
    KnowledgeCandidateService,
    KnowledgeDeduplicationService,
    KnowledgeLifecycleService,
    KnowledgeRetrievalService,
)
from engine.memory.fs_repository import FilesystemMemoryRepository
from engine.planning.fs_repository import FilesystemPlanningRepository
from engine.planning.services import (
    MilestonePlanningService,
    PlanningInitializationService,
    PlanningSummaryService,
    ScopePlanningService,
    TaskPlanningService,
)
from engine.project.fs_repository import FilesystemProjectRepository
from engine.project.services import (
    ProjectCreationService,
    ProjectLifecycleService,
    ProjectLoadingService,
    ProjectRegistryService,
)
from engine.prompt.loader import PromptLoader
from engine.research.fs_repository import FilesystemResearchRepository
from engine.research.services import (
    OpportunityAnalysisService,
    ResearchCaptureService,
    ResearchInitializationService,
    ResearchOrganizationService,
    ResearchSummaryService,
)
from engine.workflow.fs_repository import FilesystemWorkflowRepository
from engine.workflow.orchestration import (
    ArchitectureStageExecutor,
    EvaluationStageExecutor,
    PlanningStageExecutor,
    ResearchStageExecutor,
    StageServiceRegistry,
    WorkflowOrchestrationService,
)
from engine.workflow.services import (
    WorkflowInitializationService,
    WorkflowReadinessService,
    WorkflowTransitionService,
)
from presentation.collectors.collectors import (
    DiagnosticsCollector,
    KnowledgeSummaryCollector,
    ProjectDashboardCollector,
    ResearchSummaryCollector,
    WorkflowStatusCollector,
)
from presentation.orchestration import PlatformOrchestrationService
from presentation.renderers import RendererRegistry
from presentation.renderers.base import CliRenderer, JsonRenderer, MarkdownRenderer
from tests.ai.test_adapters import MockAIProvider


def create_test_platform(  # noqa: PLR0915
    tmp_path: Path, ai_provider: AIProvider | None = None
) -> Atlas:
    """Construct the test platform using the production dependency shape.

    Args:
        tmp_path: Root temp directory for the test's workspace.
        ai_provider: Optional AI provider override. Defaults to a
            ``MockAIProvider`` stubbed with ``"{}"``; pass an instance whose
            ``stubbed_response`` can be mutated between calls to drive a
            proposal through a real, non-empty stage execution.
    """
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
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
        ai_provider or MockAIProvider(stubbed_response="{}"),
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

    orchestration = WorkflowOrchestrationService(
        workflow_repo=workflow_repo,
        transition_service=workflow_transition,
        readiness_service=workflow_readiness,
        commit_service=commit_service,
        registry=registry,
        knowledge_orchestration=knowledge_orchestration,
    )
    atlas = Atlas(
        _AtlasServices(
            project_creation_service=ProjectCreationService(project_repo),
            project_loading_service=ProjectLoadingService(project_repo),
            project_listing_service=ProjectRegistryService(project_repo),
            project_archive_service=ProjectLifecycleService(project_repo),
            workflow_initialization_service=workflow_initialization,
            workflow_repo=workflow_repo,
            workflow_transition_service=workflow_transition,
            orchestration_service=orchestration,
            proposal_repo=proposal_repo,
            research_repo=research_repo,
            planning_repo=planning_repo,
            architecture_repo=architecture_repo,
            evaluation_repo=evaluation_repo,
            knowledge_repo=knowledge_repo,
        )
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
