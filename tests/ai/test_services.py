from unittest.mock import Mock
from uuid import uuid4

import pytest

from engine.ai.context import IdentityContextStrategy
from engine.ai.exceptions import InvalidContextException
from engine.ai.prompts import ResearchPromptTemplate
from engine.ai.services import AIOrchestrationService, ContextAssemblerService
from engine.domain.ai import ContextPayload
from engine.domain.ai_drafts import ResearchProposalDraft
from engine.domain.metadata import ArtifactMetadata, ArtifactStatus
from tests.ai.test_adapters import MockAIProvider


def test_context_assembler() -> None:
    svc = ContextAssemblerService(
        research_repo=Mock(),
        planning_repo=Mock(),
        architecture_repo=Mock(),
        evaluation_repo=Mock(),
        memory_repo=Mock(),
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


def test_context_assembler_rejects_missing_approved_snapshot() -> None:
    svc = ContextAssemblerService(Mock(), Mock(), Mock(), Mock(), Mock())
    aggregate = Mock()
    aggregate.snapshots = [Mock(metadata=ArtifactMetadata(status=ArtifactStatus.DRAFT))]
    svc.research_repo.get_by_project_id.return_value = aggregate  # type: ignore
    svc.planning_repo.get_by_project_id.return_value = aggregate  # type: ignore
    svc.architecture_repo.get_by_project_id.return_value = aggregate  # type: ignore
    svc.evaluation_repo.get_by_project_id.return_value = None  # type: ignore

    with pytest.raises(InvalidContextException):
        svc.assemble_context(uuid4())


def test_ai_orchestration() -> None:
    provider = MockAIProvider('{"problem_statement": "Problem", "objectives": []}')
    strategy = IdentityContextStrategy()
    svc = AIOrchestrationService(provider, strategy)

    template = ResearchPromptTemplate()
    ctx = ContextPayload(serialized_context="abc")

    draft = svc.prompt_executor.execute(template, ctx, ResearchProposalDraft)
    assert isinstance(draft, ResearchProposalDraft)
