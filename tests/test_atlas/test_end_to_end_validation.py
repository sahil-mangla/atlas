"""Sprint 5 (Phase 16) end-to-end validation of the full engineering pipeline.

Drives real project scenarios through the public Atlas facade with the
production dependency shape (real ``ProposalCommitService``, real
transformers/validators, real ``KnowledgeOrchestrationService``) and only the
AI provider itself replaced by a deterministic stub -- exercising the
generate -> approve -> commit -> transition path that, before this sprint,
was hidden behind ``Mock(spec=ProposalCommitService)`` in the shared test
fixture and never actually run.
"""

import uuid
from pathlib import Path

import pytest

from atlas import Atlas
from atlas.commands import (
    ApproveProposalCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    ListProjectsCommand,
    RejectProposalCommand,
    TransitionStageCommand,
)
from atlas.exceptions import ProjectNotFoundError, ProposalValidationError
from atlas.types import ProjectStatus, ProposalStatus, WorkflowStage
from engine.domain.ai_drafts import (
    PlanningDeliverableDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
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
    # Approving the stage's one required proposal satisfies its objectives,
    # so readiness passes and the transition proceeds automatically
    # (Finding-008 fix; previously this was permanently blocked for every
    # stage of every project, regardless of proposal quality).
    assert not commit.transition_blocked
    assert not commit.blocking_issues

    research_view = platform.get_research_summary_view(proj.id)
    assert research_view.exists is True

    dashboard = platform.get_project_dashboard_view(proj.id)
    assert dashboard.project_id == proj.id

    # Regression test (Finding-016): the Project aggregate -- what
    # `atlas project list` reports -- must reflect the real progress just
    # made, not remain stuck at its creation-time "initialized" status.
    listed = platform.list_projects(ListProjectsCommand())
    project_entry = next(p for p in listed.projects if p.id == proj.id)
    assert project_entry.status == ProjectStatus.ACTIVE


def test_planning_stage_with_deliverables_commits_end_to_end(
    platform: Atlas, provider: MockAIProvider
) -> None:
    """Regression test (Finding-017): PlanningProposalDraft.deliverables must
    carry real title/description fields the schema actually documents, not a
    bare dict -- ScopePlanningService.set_scope() hardcodes d["title"], which
    KeyErrors on any deliverable shaped some other reasonable way (e.g. a
    single free-text key), and (per Finding-014, not fixed here) the CLI
    would show no error text at all when that happened."""
    proj = platform.create_project(
        CreateProjectCommand(name="Rollback Tooling", description="D", objective="O")
    )
    platform.transition_stage(TransitionStageCommand(project_id=proj.id))
    _stub_research_draft(provider)
    research_proposal = platform.execute_stage(
        ExecuteStageCommand(project_id=proj.id, stage=WorkflowStage.RESEARCH)
    )
    research_commit = platform.approve_proposal(
        ApproveProposalCommand(project_id=proj.id, proposal_id=research_proposal.id)
    )
    assert not research_commit.transition_blocked  # research -> planning, direct

    planning_draft = PlanningProposalDraft(
        scope_statement="Ship the rollback CLI tool.",
        deliverables=[
            PlanningDeliverableDraft(
                title="Rollback Mechanism", description="Core rollback logic."
            )
        ],
    )
    provider.stubbed_response = planning_draft.model_dump_json()
    planning_proposal = platform.execute_stage(
        ExecuteStageCommand(project_id=proj.id, stage=WorkflowStage.PLANNING)
    )

    commit = platform.approve_proposal(
        ApproveProposalCommand(project_id=proj.id, proposal_id=planning_proposal.id)
    )
    assert commit.success
    assert not commit.transition_blocked
    assert not commit.blocking_issues


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
