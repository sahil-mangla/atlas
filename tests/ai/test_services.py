from unittest.mock import Mock
from uuid import uuid4

import pytest

from engine.ai.context import IdentityContextStrategy
from engine.ai.exceptions import InvalidContextException
from engine.ai.executor import PromptExecutor
from engine.ai.services import AIOrchestrationService, ContextAssemblerService
from engine.domain.ai import ContextPayload
from engine.domain.ai_drafts import ResearchProposalDraft
from engine.domain.enums import WorkflowStage
from engine.domain.metadata import ArtifactMetadata, ArtifactStatus
from engine.prompt.loader import PromptLoader
from tests.ai.test_adapters import MockAIProvider


def _fake_project() -> Mock:
    project = Mock()
    project.name = "CSV Schema Validator"
    project.description = "Validates CSV files against a declared JSON schema."
    project.objective = "Ship a working validator with test coverage."
    return project


def test_context_assembler() -> None:
    svc = ContextAssemblerService(
        research_repo=Mock(),
        planning_repo=Mock(),
        architecture_repo=Mock(),
        evaluation_repo=Mock(),
        memory_repo=Mock(),
        project_repo=Mock(),
    )
    snapshot = Mock()
    snapshot.metadata = ArtifactMetadata(status=ArtifactStatus.APPROVED)
    snapshot.model_dump_json.return_value = '{"approved": true}'
    aggregate = Mock()
    aggregate.snapshots = [snapshot]
    svc.research_repo.get_by_project_id.return_value = aggregate  # type: ignore
    svc.planning_repo.get_by_project_id.return_value = aggregate  # type: ignore
    svc.architecture_repo.get_by_project_id.return_value = aggregate  # type: ignore
    svc.evaluation_repo.get_by_project_id.return_value = None  # type: ignore

    ctx = svc.assemble_context(uuid4())
    assert isinstance(ctx, ContextPayload)
    assert "Context" in ctx.serialized_context


def test_context_assembler_includes_project_definition() -> None:
    """Regression test: the AI must be told what the project actually is
    (name/description/objective), not just its UUID (Finding-007)."""
    svc = ContextAssemblerService(Mock(), Mock(), Mock(), Mock(), Mock(), Mock())
    svc.research_repo.get_by_project_id.return_value = None  # type: ignore
    svc.planning_repo.get_by_project_id.return_value = None  # type: ignore
    svc.architecture_repo.get_by_project_id.return_value = None  # type: ignore
    svc.evaluation_repo.get_by_project_id.return_value = None  # type: ignore
    svc.project_repo.get_by_id.return_value = _fake_project()  # type: ignore

    ctx = svc.assemble_context(uuid4(), stage=WorkflowStage.RESEARCH)

    assert "## Project Definition" in ctx.serialized_context
    assert "CSV Schema Validator" in ctx.serialized_context
    assert (
        "Validates CSV files against a declared JSON schema." in ctx.serialized_context
    )
    assert "Ship a working validator with test coverage." in ctx.serialized_context


def test_context_assembler_rejects_missing_approved_snapshot() -> None:
    """Planning requires an approved Research snapshot to exist first."""
    svc = ContextAssemblerService(Mock(), Mock(), Mock(), Mock(), Mock(), Mock())
    aggregate = Mock()
    aggregate.snapshots = [Mock(metadata=ArtifactMetadata(status=ArtifactStatus.DRAFT))]
    svc.research_repo.get_by_project_id.return_value = aggregate  # type: ignore
    svc.planning_repo.get_by_project_id.return_value = aggregate  # type: ignore
    svc.architecture_repo.get_by_project_id.return_value = aggregate  # type: ignore
    svc.evaluation_repo.get_by_project_id.return_value = None  # type: ignore

    with pytest.raises(InvalidContextException):
        svc.assemble_context(uuid4(), stage=WorkflowStage.PLANNING)


def test_context_assembler_research_stage_requires_no_prior_snapshot() -> None:
    """Research is the pipeline's first stage: it must not require any
    subsystem's approved snapshot to already exist (regression test for the
    bug where assemble_context unconditionally required all four snapshots,
    making it impossible to ever generate the first Research proposal)."""
    svc = ContextAssemblerService(Mock(), Mock(), Mock(), Mock(), Mock(), Mock())
    svc.research_repo.get_by_project_id.return_value = None  # type: ignore
    svc.planning_repo.get_by_project_id.return_value = None  # type: ignore
    svc.architecture_repo.get_by_project_id.return_value = None  # type: ignore
    svc.evaluation_repo.get_by_project_id.return_value = None  # type: ignore

    ctx = svc.assemble_context(uuid4(), stage=WorkflowStage.RESEARCH)

    assert ctx.research_snapshot_id is None
    assert "None" in ctx.serialized_context


def test_ai_orchestration() -> None:
    provider = MockAIProvider('{"problem_statement": "Problem", "objectives": []}')
    strategy = IdentityContextStrategy()
    registry = PromptLoader.load_registry()
    executor = PromptExecutor(provider, strategy)
    svc = AIOrchestrationService(executor, registry)

    ctx = ContextPayload(serialized_context="abc")

    draft = svc.prompt_executor.execute(
        registry.resolve(ResearchProposalDraft),
        ctx,
        ResearchProposalDraft,
    )
    assert isinstance(draft, ResearchProposalDraft)
