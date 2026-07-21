"""Sprint 5 (Phase 16) end-to-end validation of the full engineering pipeline.

Drives real project scenarios through the public Atlas facade with the
production dependency shape (real ``ProposalCommitService``, real
transformers/validators, real ``KnowledgeOrchestrationService``) and only the
AI provider itself replaced by a deterministic stub -- exercising the
generate -> approve -> commit -> (blocked) transition path that, before this
sprint, was hidden behind ``Mock(spec=ProposalCommitService)`` in the shared
test fixture and never actually run.
"""

import uuid
from pathlib import Path

import pytest

from atlas import Atlas
from atlas.commands import (
    ApproveProposalCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    RejectProposalCommand,
    TransitionStageCommand,
)
from atlas.exceptions import ProjectNotFoundError, ProposalValidationError
from atlas.types import ProposalStatus, WorkflowStage
from engine.domain.ai_drafts import ResearchProposalDraft
from tests.ai.test_adapters import MockAIProvider
from tests.support.test_bootstrap import create_test_platform


@pytest.fixture
def provider() -> MockAIProvider:
    return MockAIProvider(stubbed_response="{}")


@pytest.fixture
def platform(tmp_path: Path, provider: MockAIProvider) -> Atlas:
    return create_test_platform(tmp_path, ai_provider=provider)


def _stub_research_draft(provider: MockAIProvider) -> ResearchProposalDraft:
    draft = ResearchProposalDraft(
        problem_statement="Users cannot recover from a failed deployment.",
        objectives=["Design a rollback mechanism", "Document the recovery runbook"],
    )
    provider.stubbed_response = draft.model_dump_json()
    return draft


def test_research_stage_proposal_commits_successfully_end_to_end(
    platform: Atlas, provider: MockAIProvider
) -> None:
    """A real Research proposal, once approved, actually commits -- not a Mock."""
    proj = platform.create_project(
        CreateProjectCommand(name="Rollback Tooling", description="D", objective="O")
    )
    platform.transition_stage(TransitionStageCommand(project_id=proj.id))

    draft = _stub_research_draft(provider)
    proposal = platform.execute_stage(
        ExecuteStageCommand(project_id=proj.id, stage=WorkflowStage.RESEARCH)
    )
    assert proposal.status == ProposalStatus.DRAFT
    assert proposal.content["problem_statement"] == draft.problem_statement

    commit = platform.approve_proposal(
        ApproveProposalCommand(project_id=proj.id, proposal_id=proposal.id)
    )
    assert commit.success
    # Objectives are not auto-completed by proposal approval, so readiness
    # correctly blocks the automatic stage transition -- and the public
    # CommitResult now says so explicitly (Sprint 5 fix; previously silent).
    assert commit.transition_blocked
    assert commit.blocking_issues

    research_view = platform.get_research_summary_view(proj.id)
    assert research_view.exists is True

    dashboard = platform.get_project_dashboard_view(proj.id)
    assert dashboard.project_id == proj.id


def test_reject_then_retry_recovery_flow(
    platform: Atlas, provider: MockAIProvider
) -> None:
    """Rejecting a proposal must not commit it; a subsequent approval still can."""
    proj = platform.create_project(
        CreateProjectCommand(name="Recovery Flow", description="D", objective="O")
    )
    platform.transition_stage(TransitionStageCommand(project_id=proj.id))

    _stub_research_draft(provider)
    first = platform.execute_stage(
        ExecuteStageCommand(project_id=proj.id, stage=WorkflowStage.RESEARCH)
    )
    platform.reject_proposal(
        RejectProposalCommand(
            project_id=proj.id, proposal_id=first.id, feedback="Needs more evidence."
        )
    )

    # Rejected proposal must not have been committed.
    research_view = platform.get_research_summary_view(proj.id)
    assert research_view.exists is False

    # The rejected proposal is no longer approvable.
    with pytest.raises(ProposalValidationError):
        platform.approve_proposal(
            ApproveProposalCommand(project_id=proj.id, proposal_id=first.id)
        )

    # Recovery: regenerate and approve.
    _stub_research_draft(provider)
    second = platform.execute_stage(
        ExecuteStageCommand(project_id=proj.id, stage=WorkflowStage.RESEARCH)
    )
    commit = platform.approve_proposal(
        ApproveProposalCommand(project_id=proj.id, proposal_id=second.id)
    )
    assert commit.success

    research_view = platform.get_research_summary_view(proj.id)
    assert research_view.exists is True


def test_invalid_project_id_raises_not_found(platform: Atlas) -> None:
    """Operating on a nonexistent project ID must fail with a typed error,
    not a silent no-op or an internal exception leaking through the facade."""
    bogus_id = uuid.uuid4()

    with pytest.raises(ProjectNotFoundError):
        platform.get_project_dashboard_view(bogus_id)


def test_empty_project_has_no_research_before_any_stage_runs(platform: Atlas) -> None:
    """A freshly created project (the 'empty project' scenario) must present
    a well-defined empty state, not raise or return partially-populated data."""
    proj = platform.create_project(
        CreateProjectCommand(name="Empty", description="D", objective="O")
    )

    research_view = platform.get_research_summary_view(proj.id)
    assert research_view.exists is False

    diagnostics = platform.get_diagnostics_view(proj.id)
    assert diagnostics.issues
