import json
from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

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
from engine.ai.exceptions import InvalidProposalException
from engine.ai.services import ContextAssemblerService
from engine.domain.ai import AIProposal, ContextPayload, PromptTemplateMetadata
from engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    EvaluationProposalDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
from engine.domain.enums import ProposalStatus, ProposalType
from tests.ai.test_adapters import MockAIProvider


# Mock repos that implement basic lookup and save for state rollback verification
class MockRepo:
    def __init__(self) -> None:
        self.state: Any = None

    def get_by_project_id(self, project_id: UUID) -> Any:
        return self.state

    def save(self, obj: Any) -> None:
        self.state = obj


@pytest.fixture
def assembler() -> ContextAssemblerService:
    assembler = Mock(spec=ContextAssemblerService)
    assembler.assemble_context.return_value = ContextPayload(
        serialized_context="Mock Context"
    )
    return assembler


def test_research_ai_service(assembler: ContextAssemblerService) -> None:
    draft_data = ResearchProposalDraft(
        problem_statement="Build atomic engine",
        objectives=["Speed", "Decoupling"],
        evidence=[],
    )
    orchestrator = Mock()
    meta = PromptTemplateMetadata(version=1, supported_subsystem=ProposalType.RESEARCH)
    orchestrator.generate_proposal.return_value = AIProposal[dict[str, Any]](
        proposal_type=ProposalType.RESEARCH,
        status=ProposalStatus.DRAFT,
        prompt_metadata=meta,
        context_used=ContextPayload(serialized_context=""),
        data={"raw_content": draft_data.model_dump_json()},
    )

    service = ResearchAIEngineeringService(orchestrator, assembler)
    proposal = service.generate(uuid4())

    assert isinstance(proposal, AIProposal)
    assert proposal.data.problem_statement == "Build atomic engine"
    assert len(proposal.data.objectives) == 2


def test_planning_ai_service(assembler: ContextAssemblerService) -> None:
    draft_data = PlanningProposalDraft(
        scope_statement="Build Scope",
        deliverables=[{"title": "Deliv 1", "description": ""}],
        milestones=[],
    )
    orchestrator = Mock()
    meta = PromptTemplateMetadata(version=1, supported_subsystem=ProposalType.PLANNING)
    orchestrator.generate_proposal.return_value = AIProposal[dict[str, Any]](
        proposal_type=ProposalType.PLANNING,
        status=ProposalStatus.DRAFT,
        prompt_metadata=meta,
        context_used=ContextPayload(serialized_context=""),
        data={"raw_content": draft_data.model_dump_json()},
    )

    service = PlanningAIEngineeringService(orchestrator, assembler)
    proposal = service.generate(uuid4())
    assert proposal.data.scope_statement == "Build Scope"


def test_architecture_ai_service(assembler: ContextAssemblerService) -> None:
    draft_data = ArchitectureProposalDraft(
        design_summary="Design summary",
        components=[],
        decisions=[],
    )
    orchestrator = Mock()
    meta = PromptTemplateMetadata(version=1, supported_subsystem=ProposalType.ARCHITECTURE)
    orchestrator.generate_proposal.return_value = AIProposal[dict[str, Any]](
        proposal_type=ProposalType.ARCHITECTURE,
        status=ProposalStatus.DRAFT,
        prompt_metadata=meta,
        context_used=ContextPayload(serialized_context=""),
        data={"raw_content": draft_data.model_dump_json()},
    )

    service = ArchitectureAIEngineeringService(orchestrator, assembler)
    proposal = service.generate(uuid4())
    assert proposal.data.design_summary == "Design summary"


def test_evaluation_ai_service(assembler: ContextAssemblerService) -> None:
    draft_data = EvaluationProposalDraft(
        synthesis="Quality looks good",
        findings=[],
    )
    orchestrator = Mock()
    meta = PromptTemplateMetadata(version=1, supported_subsystem=ProposalType.EVALUATION)
    orchestrator.generate_proposal.return_value = AIProposal[dict[str, Any]](
        proposal_type=ProposalType.EVALUATION,
        status=ProposalStatus.DRAFT,
        prompt_metadata=meta,
        context_used=ContextPayload(serialized_context=""),
        data={"raw_content": draft_data.model_dump_json()},
    )

    service = EvaluationAIEngineeringService(orchestrator, assembler)
    proposal = service.generate(uuid4())
    assert proposal.data.synthesis == "Quality looks good"


def test_proposal_commit_atomic_rollback() -> None:
    project_id = uuid4()
    
    research_repo = MockRepo()
    planning_repo = MockRepo()
    architecture_repo = MockRepo()
    evaluation_repo = MockRepo()

    # Pre-populate state
    mock_original_research = Mock()
    mock_original_research.model_copy.return_value = mock_original_research
    research_repo.state = mock_original_research

    transformer = Mock(spec=ResearchProposalTransformer)
    transformer.transform_and_commit.side_effect = RuntimeError("Crash during commit")
    validator = ResearchProposalValidator()

    commit_service = ProposalCommitService(
        research_repo=research_repo,  # type: ignore
        planning_repo=planning_repo,  # type: ignore
        architecture_repo=architecture_repo,  # type: ignore
        evaluation_repo=evaluation_repo,  # type: ignore
        research_transformer=transformer,
        planning_transformer=Mock(),
        architecture_transformer=Mock(),
        evaluation_transformer=Mock(),
        research_validator=validator,
        planning_validator=Mock(),
        architecture_validator=Mock(),
        evaluation_validator=Mock(),
    )

    meta = PromptTemplateMetadata(version=1, supported_subsystem=ProposalType.RESEARCH)
    proposal = AIProposal[ResearchProposalDraft](
        proposal_type=ProposalType.RESEARCH,
        status=ProposalStatus.APPROVED,
        prompt_metadata=meta,
        context_used=ContextPayload(serialized_context=""),
        data=ResearchProposalDraft(
            problem_statement="Test statement",
            objectives=["Obj 1"],
        )
    )

    res = commit_service.commit_proposal(project_id, proposal)

    assert not res.success
    assert "Atomic commit failed" in res.errors[0]
    assert research_repo.state is mock_original_research


def test_proposal_validation_failure() -> None:
    commit_service = ProposalCommitService(
        research_repo=Mock(),
        planning_repo=Mock(),
        architecture_repo=Mock(),
        evaluation_repo=Mock(),
        research_transformer=Mock(),
        planning_transformer=Mock(),
        architecture_transformer=Mock(),
        evaluation_transformer=Mock(),
        research_validator=ResearchProposalValidator(),
        planning_validator=Mock(),
        architecture_validator=Mock(),
        evaluation_validator=Mock(),
    )

    meta = PromptTemplateMetadata(version=1, supported_subsystem=ProposalType.RESEARCH)
    proposal = AIProposal[ResearchProposalDraft](
        proposal_type=ProposalType.RESEARCH,
        status=ProposalStatus.APPROVED,
        prompt_metadata=meta,
        context_used=ContextPayload(serialized_context=""),
        data=ResearchProposalDraft(
            problem_statement="",  # Invalid
            objectives=[],
        )
    )

    res = commit_service.commit_proposal(uuid4(), proposal)
    assert not res.success
    assert "Problem statement cannot be empty" in res.errors[0]
