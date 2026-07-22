"""RC-002 regression: knowledge candidates can be listed, shown, approved,
and rejected through the public Atlas facade -- the same surface the CLI's
``atlas knowledge ...`` commands dispatch to.

Before this fix, ``KnowledgeOrchestrationService`` had no way to list all
candidates or fetch one by ID, and ``ReviewKnowledgeCandidateCommand`` --
though it existed on the facade -- had zero CLI exposure (no parser branch,
no application dispatch, no renderer).
"""

import uuid
from pathlib import Path
from uuid import UUID

import pytest

from atlas import Atlas
from atlas.commands import (
    ApproveProposalCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    KnowledgeActorInput,
    ListKnowledgeCandidatesCommand,
    ReviewKnowledgeCandidateCommand,
    ShowKnowledgeCandidateCommand,
    TransitionStageCommand,
)
from atlas.exceptions import ApplicationError
from atlas.types import (
    KnowledgeActorType,
    KnowledgeCandidateStatus,
    ProposalDecision,
    WorkflowStage,
)
from engine.domain.ai_drafts import (
    ResearchEvidenceDraft,
    ResearchFindingDraft,
    ResearchProposalDraft,
)
from tests.ai.test_adapters import MockAIProvider
from tests.support.test_bootstrap import create_test_platform


@pytest.fixture
def provider() -> MockAIProvider:
    return MockAIProvider(stubbed_response="{}")


@pytest.fixture
def platform_with_candidate(
    tmp_path: Path, provider: MockAIProvider
) -> tuple[Atlas, UUID]:
    """A project with one pending knowledge candidate, extracted from a
    committed research proposal -- the real path candidates come from."""
    platform = create_test_platform(tmp_path, ai_provider=provider)
    proj = platform.create_project(
        CreateProjectCommand(name="Knowledge CLI", description="D", objective="O")
    )
    platform.transition_stage(TransitionStageCommand(project_id=proj.id))

    draft = ResearchProposalDraft(
        problem_statement="Users cannot recover from a failed deployment.",
        objectives=["Design a rollback mechanism"],
        evidence=[
            ResearchEvidenceDraft(
                title="Incident postmortem",
                summary="Deploy #482 had no rollback path and caused an outage.",
            )
        ],
        findings=[
            ResearchFindingDraft(
                title="Deploys lack a rollback path",
                summary="No automated way to revert a bad deploy today.",
                evidence_indices=[0],
            )
        ],
    )
    provider.stubbed_response = draft.model_dump_json()
    proposal = platform.execute_stage(
        ExecuteStageCommand(project_id=proj.id, stage=WorkflowStage.RESEARCH)
    )
    platform.approve_proposal(
        ApproveProposalCommand(project_id=proj.id, proposal_id=proposal.id)
    )
    return platform, proj.id


def test_list_knowledge_candidates_finds_extracted_candidate(
    platform_with_candidate: tuple[Atlas, UUID],
) -> None:
    platform, project_id = platform_with_candidate
    result = platform.list_knowledge_candidates(
        ListKnowledgeCandidatesCommand(project_id=project_id)
    )
    assert len(result.candidates) == 1
    assert result.candidates[0].title == "Deploys lack a rollback path"
    assert result.candidates[0].status == KnowledgeCandidateStatus.PENDING_REVIEW.value


def test_list_knowledge_candidates_filters_by_status(
    platform_with_candidate: tuple[Atlas, UUID],
) -> None:
    platform, project_id = platform_with_candidate
    result = platform.list_knowledge_candidates(
        ListKnowledgeCandidatesCommand(
            project_id=project_id, status=KnowledgeCandidateStatus.REJECTED
        )
    )
    assert result.candidates == []


def test_show_knowledge_candidate(
    platform_with_candidate: tuple[Atlas, UUID],
) -> None:
    platform, project_id = platform_with_candidate
    listed = platform.list_knowledge_candidates(
        ListKnowledgeCandidatesCommand(project_id=project_id)
    )
    candidate_id = listed.candidates[0].id

    shown = platform.show_knowledge_candidate(
        ShowKnowledgeCandidateCommand(project_id=project_id, candidate_id=candidate_id)
    )
    assert shown.id == candidate_id
    assert shown.content == "No automated way to revert a bad deploy today."


def test_show_knowledge_candidate_not_found_raises(
    platform_with_candidate: tuple[Atlas, UUID],
) -> None:
    platform, project_id = platform_with_candidate
    with pytest.raises(ApplicationError):
        platform.show_knowledge_candidate(
            ShowKnowledgeCandidateCommand(
                project_id=project_id, candidate_id=uuid.uuid4()
            )
        )


def test_approve_knowledge_candidate_publishes_it(
    platform_with_candidate: tuple[Atlas, UUID],
) -> None:
    """Approval is also the only publish step -- there is no separate
    publish action in the engine."""
    platform, project_id = platform_with_candidate
    listed = platform.list_knowledge_candidates(
        ListKnowledgeCandidatesCommand(project_id=project_id)
    )
    candidate_id = listed.candidates[0].id

    result = platform.review_knowledge_candidate(
        ReviewKnowledgeCandidateCommand(
            project_id=project_id,
            candidate_id=candidate_id,
            decision=ProposalDecision.APPROVE,
            actor=KnowledgeActorInput(
                actor_type=KnowledgeActorType.HUMAN, actor_id="reviewer"
            ),
        )
    )
    assert result.success

    after = platform.list_knowledge_candidates(
        ListKnowledgeCandidatesCommand(project_id=project_id)
    )
    assert after.candidates[0].status == KnowledgeCandidateStatus.APPROVED.value

    published = platform.get_knowledge_read_model(project_id)
    assert published.published_count == 1


def test_reject_knowledge_candidate_does_not_publish(
    platform_with_candidate: tuple[Atlas, UUID],
) -> None:
    platform, project_id = platform_with_candidate
    listed = platform.list_knowledge_candidates(
        ListKnowledgeCandidatesCommand(project_id=project_id)
    )
    candidate_id = listed.candidates[0].id

    result = platform.review_knowledge_candidate(
        ReviewKnowledgeCandidateCommand(
            project_id=project_id,
            candidate_id=candidate_id,
            decision=ProposalDecision.REJECT,
            actor=KnowledgeActorInput(
                actor_type=KnowledgeActorType.HUMAN, actor_id="reviewer"
            ),
            feedback="Not generalizable enough.",
        )
    )
    assert result.success

    after = platform.list_knowledge_candidates(
        ListKnowledgeCandidatesCommand(project_id=project_id)
    )
    assert after.candidates[0].status == KnowledgeCandidateStatus.REJECTED.value

    published = platform.get_knowledge_read_model(project_id)
    assert published.published_count == 0
