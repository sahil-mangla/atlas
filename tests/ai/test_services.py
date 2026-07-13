from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from engine.ai.context import IdentityContextStrategy
from engine.ai.exceptions import InvalidProposalException
from engine.ai.prompts import ResearchPromptTemplate
from engine.ai.services import AIOrchestrationService, ContextAssemblerService, ProposalCommitService
from engine.domain.ai import AIProposal, ContextPayload
from engine.domain.enums import ProposalStatus, ProposalType
from tests.ai.test_adapters import MockAIProvider


def test_context_assembler() -> None:
    svc = ContextAssemblerService(
        research_repo=Mock(),
        planning_repo=Mock(),
        architecture_repo=Mock(),
        evaluation_repo=Mock(),
        memory_repo=Mock(),
    )
    # Configure mocks to return None or objects with no snapshots
    svc.research_repo.get_by_project_id.return_value = None  # type: ignore
    svc.planning_repo.get_by_project_id.return_value = None  # type: ignore
    svc.architecture_repo.get_by_project_id.return_value = None  # type: ignore
    svc.evaluation_repo.get_by_project_id.return_value = None  # type: ignore

    ctx = svc.assemble_context(uuid4())
    assert isinstance(ctx, ContextPayload)
    assert "Context" in ctx.serialized_context


def test_ai_orchestration() -> None:
    provider = MockAIProvider('{"summary": "Mock output"}')
    strategy = IdentityContextStrategy()
    svc = AIOrchestrationService(provider, strategy)
    
    template = ResearchPromptTemplate()
    ctx = ContextPayload(serialized_context="abc")
    
    proposal = svc.generate_proposal(template, ctx)
    assert isinstance(proposal, AIProposal)
    assert proposal.status == ProposalStatus.DRAFT
    assert proposal.proposal_type == template.metadata.supported_subsystem
    assert proposal.data["raw_content"] == '{"summary": "Mock output"}'


def test_proposal_commit_service() -> None:
    svc = ProposalCommitService()
    
    # Only APPROVED can be committed
    proposal = AIProposal[dict[str, str]](
        proposal_type=ProposalType.RESEARCH,
        status=ProposalStatus.DRAFT,
        prompt_metadata=ResearchPromptTemplate().metadata,
        context_used=ContextPayload(serialized_context=""),
        data={},
    )
    with pytest.raises(InvalidProposalException):
        svc.commit_proposal(proposal)

    # Approved should pass validation
    proposal.status = ProposalStatus.APPROVED
    svc.commit_proposal(proposal)  # Should not raise
