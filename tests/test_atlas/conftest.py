"""Shared fixtures for Atlas application layer tests."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from atlas._service import Atlas
from engine.ai.context import IdentityContextStrategy
from engine.ai.engineering_services import (
    ArchitectureAIEngineeringService,
    EvaluationAIEngineeringService,
    PlanningAIEngineeringService,
    ProposalCommitService,
    ResearchAIEngineeringService,
)
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


@pytest.fixture
def test_atlas_platform(tmp_path: Path) -> Atlas:
    """Construct an Atlas platform backed by temporary filesystem repositories.

    This acts as a test-specific version of Bootstrap that does not rely
    on environment variables or the real filesystem workspace.
    """
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    project_repo = FilesystemProjectRepository(workspace_root)
    workflow_repo = FilesystemWorkflowRepository(project_repo)

    project_creation_service = ProjectCreationService(project_repo)
    project_loading_service = ProjectLoadingService(project_repo)
    project_listing_service = ProjectRegistryService(project_repo)
    project_archive_service = ProjectLifecycleService(project_repo)

    provider = MockAIProvider(stubbed_response="{}")
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

    commit_service = Mock(spec=ProposalCommitService)
    ai_orchestrator = AIOrchestrationService(provider, IdentityContextStrategy())
    research_ai = ResearchAIEngineeringService(ai_orchestrator, context_assembler)
    planning_ai = PlanningAIEngineeringService(ai_orchestrator, context_assembler)
    architecture_ai = ArchitectureAIEngineeringService(
        ai_orchestrator, context_assembler
    )
    evaluation_ai = EvaluationAIEngineeringService(ai_orchestrator, context_assembler)

    registry = StageServiceRegistry(
        {
            WorkflowStage.RESEARCH: ResearchStageExecutor(research_ai),
            WorkflowStage.PLANNING: PlanningStageExecutor(planning_ai),
            WorkflowStage.ARCHITECTURE: ArchitectureStageExecutor(architecture_ai),
            WorkflowStage.REVIEW: EvaluationStageExecutor(evaluation_ai),
        }
    )

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

    return Atlas(
        project_creation_service=project_creation_service,
        project_loading_service=project_loading_service,
        project_listing_service=project_listing_service,
        project_archive_service=project_archive_service,
        workflow_initialization_service=workflow_initialization_service,
        workflow_repo=workflow_repo,
        workflow_transition_service=workflow_transition_service,
        orchestration_service=orchestration_service,
    )
