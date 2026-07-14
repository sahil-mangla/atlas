"""Test composition root for the public Atlas SDK."""

from pathlib import Path
from unittest.mock import Mock

from atlas._service import Atlas, _AtlasServices
from engine.ai.context import IdentityContextStrategy
from engine.ai.engineering_services import (
    ArchitectureAIEngineeringService,
    EvaluationAIEngineeringService,
    PlanningAIEngineeringService,
    ProposalCommitService,
    ResearchAIEngineeringService,
)
from engine.ai.fs_repository import FilesystemProposalRepository
from engine.ai.services import AIOrchestrationService, ContextAssemblerService
from engine.architecture.fs_repository import FilesystemArchitectureRepository
from engine.domain.enums import WorkflowStage
from engine.evaluation.fs_repository import FilesystemEvaluationRepository
from engine.memory.fs_repository import FilesystemMemoryRepository
from engine.planning.fs_repository import FilesystemPlanningRepository
from engine.project.fs_repository import FilesystemProjectRepository
from engine.project.services import (
    ProjectCreationService,
    ProjectLifecycleService,
    ProjectLoadingService,
    ProjectRegistryService,
)
from engine.research.fs_repository import FilesystemResearchRepository
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
from tests.ai.test_adapters import MockAIProvider


def create_test_platform(tmp_path: Path) -> Atlas:
    """Construct the test platform using the production dependency shape."""
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
    context_assembler = ContextAssemblerService(
        research_repo=research_repo,
        planning_repo=planning_repo,
        architecture_repo=architecture_repo,
        evaluation_repo=evaluation_repo,
        memory_repo=memory_repo,
    )
    orchestrator = AIOrchestrationService(
        MockAIProvider(stubbed_response="{}"), IdentityContextStrategy()
    )
    research_ai = ResearchAIEngineeringService(orchestrator, context_assembler)
    planning_ai = PlanningAIEngineeringService(orchestrator, context_assembler)
    architecture_ai = ArchitectureAIEngineeringService(orchestrator, context_assembler)
    evaluation_ai = EvaluationAIEngineeringService(orchestrator, context_assembler)
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
    orchestration = WorkflowOrchestrationService(
        workflow_repo=workflow_repo,
        transition_service=workflow_transition,
        readiness_service=workflow_readiness,
        commit_service=Mock(spec=ProposalCommitService),
        registry=registry,
    )
    return Atlas(
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
        )
    )
