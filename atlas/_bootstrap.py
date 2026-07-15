"""Bootstrap composition root for the ATLAS engineering platform.

This module is an internal implementation detail and must not be imported
by client adapters. It wires the engine subsystems and returns the public facade.
"""

from atlas._service import Atlas, _AtlasServices
from engine.ai.adapters.gemini import GeminiAIProvider
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
from engine.ai.fs_repository import FilesystemProposalRepository
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
from engine.config import get_settings
from engine.domain.enums import WorkflowStage
from engine.evaluation.fs_repository import FilesystemEvaluationRepository
from engine.evaluation.services import (
    EvaluationInitializationService,
    EvaluationSummaryService,
    ReadinessEvaluationService,
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


def _create_platform() -> Atlas:  # noqa: PLR0915
    """Construct and wire the full ATLAS platform.

    Returns:
        The fully configured Atlas facade instance.
    """
    settings = get_settings()

    # 1. Repositories
    project_repo = FilesystemProjectRepository(settings.workspace_root)
    workflow_repo = FilesystemWorkflowRepository(project_repo)
    proposal_repo = FilesystemProposalRepository(project_repo)

    # 2. Project Services
    project_creation_service = ProjectCreationService(project_repo)
    project_loading_service = ProjectLoadingService(project_repo)
    project_listing_service = ProjectRegistryService(project_repo)
    project_archive_service = ProjectLifecycleService(project_repo)

    # 3. AI Components
    provider = GeminiAIProvider(settings)
    research_repo = FilesystemResearchRepository(project_repo)
    planning_repo = FilesystemPlanningRepository(project_repo)
    architecture_repo = FilesystemArchitectureRepository(project_repo)
    evaluation_repo = FilesystemEvaluationRepository(project_repo)
    memory_repo = FilesystemMemoryRepository(project_repo)

    context_assembler = ContextAssemblerService(
        research_repo=research_repo,
        planning_repo=planning_repo,
        architecture_repo=architecture_repo,
        evaluation_repo=evaluation_repo,
        memory_repo=memory_repo,
    )

    # 4. Subsystem services used by proposal transformers
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

    # 5. AI Engineering Services
    ai_orchestrator = AIOrchestrationService(provider, IdentityContextStrategy())
    research_ai = ResearchAIEngineeringService(ai_orchestrator, context_assembler)
    planning_ai = PlanningAIEngineeringService(ai_orchestrator, context_assembler)
    architecture_ai = ArchitectureAIEngineeringService(
        ai_orchestrator, context_assembler
    )
    evaluation_ai = EvaluationAIEngineeringService(ai_orchestrator, context_assembler)

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

    # 6. Stage Executors
    registry = StageServiceRegistry(
        {
            WorkflowStage.RESEARCH: ResearchStageExecutor(research_ai),
            WorkflowStage.PLANNING: PlanningStageExecutor(planning_ai),
            WorkflowStage.ARCHITECTURE: ArchitectureStageExecutor(architecture_ai),
            WorkflowStage.REVIEW: EvaluationStageExecutor(evaluation_ai),
        }
    )

    # 7. Workflow Orchestration
    workflow_initialization_service = WorkflowInitializationService(workflow_repo)
    workflow_transition_service = WorkflowTransitionService(workflow_repo)
    workflow_readiness_service = WorkflowReadinessService(workflow_repo)

    orchestration_service = WorkflowOrchestrationService(
        workflow_repo=workflow_repo,
        transition_service=workflow_transition_service,
        readiness_service=workflow_readiness_service,
        commit_service=commit_service,
        registry=registry,
    )

    # 8. Facade Assembly
    return Atlas(
        _AtlasServices(
            project_creation_service=project_creation_service,
            project_loading_service=project_loading_service,
            project_listing_service=project_listing_service,
            project_archive_service=project_archive_service,
            workflow_initialization_service=workflow_initialization_service,
            workflow_repo=workflow_repo,
            workflow_transition_service=workflow_transition_service,
            orchestration_service=orchestration_service,
            proposal_repo=proposal_repo,
        )
    )
