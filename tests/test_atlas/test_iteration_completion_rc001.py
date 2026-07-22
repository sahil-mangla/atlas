"""RC-001 regression: a project must be able to reach the terminal workflow
stage using only supported public interfaces.

Before this fix, ``WorkflowTransitionService.transition_stage`` set
``active_objectives`` for every stage (including human-driven stages with no
AI StageExecutor -- PROBLEM_DEFINITION, IMPLEMENTATION, ITERATION,
COMPLETION), but nothing reachable from the public Atlas facade could ever
clear them for those stages: ``WorkflowReadinessService.evaluate_readiness``
fails while any objective remains active, so ``workflow transition``
permanently 400'd once a project reached ITERATION. This is a dead end
CreateProjectCommand -> ... -> ITERATION -> (stuck forever).
"""

from pathlib import Path
from uuid import UUID

import pytest

from atlas import Atlas
from atlas.commands import (
    ApproveProposalCommand,
    CompleteObjectiveCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    GetWorkflowStatusCommand,
    TransitionStageCommand,
)
from atlas.exceptions import ApplicationError
from atlas.types import WorkflowStage
from engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    EvaluationFindingDraft,
    EvaluationProposalDraft,
    PlanningDeliverableDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
from engine.domain.enums import FindingCategory, FindingSeverity
from tests.ai.test_adapters import MockAIProvider
from tests.support.test_bootstrap import create_test_platform

_StageDraft = (
    ResearchProposalDraft
    | PlanningProposalDraft
    | ArchitectureProposalDraft
    | EvaluationProposalDraft
)


@pytest.fixture
def provider() -> MockAIProvider:
    return MockAIProvider(stubbed_response="{}")


@pytest.fixture
def platform(tmp_path: Path, provider: MockAIProvider) -> Atlas:
    return create_test_platform(tmp_path, ai_provider=provider)


def _run_ai_stage(
    platform: Atlas,
    provider: MockAIProvider,
    project_id: UUID,
    stage: WorkflowStage,
    draft: _StageDraft,
) -> None:
    provider.stubbed_response = draft.model_dump_json()
    proposal = platform.execute_stage(
        ExecuteStageCommand(project_id=project_id, stage=stage)
    )
    commit = platform.approve_proposal(
        ApproveProposalCommand(project_id=project_id, proposal_id=proposal.id)
    )
    assert commit.success
    assert not commit.transition_blocked


def test_project_reaches_completion_via_public_interfaces_only(
    platform: Atlas, provider: MockAIProvider
) -> None:
    """Idea -> Research -> Planning -> Architecture -> Review -> Iteration ->
    Completion, driven entirely through Atlas commands -- no direct
    repository/engine access, no undocumented workaround."""
    proj = platform.create_project(
        CreateProjectCommand(name="RC-001", description="D", objective="O")
    )

    # IDEA -> RESEARCH (auto-ready, no objectives required)
    platform.transition_stage(TransitionStageCommand(project_id=proj.id))
    assert (
        platform.get_workflow_status(
            GetWorkflowStatusCommand(project_id=proj.id)
        ).current_stage
        == WorkflowStage.RESEARCH
    )

    _run_ai_stage(
        platform,
        provider,
        proj.id,
        WorkflowStage.RESEARCH,
        ResearchProposalDraft(
            problem_statement="Users cannot recover from a failed deployment.",
            objectives=["Design a rollback mechanism", "Document the runbook"],
        ),
    )  # RESEARCH -> PLANNING

    _run_ai_stage(
        platform,
        provider,
        proj.id,
        WorkflowStage.PLANNING,
        PlanningProposalDraft(
            scope_statement="Ship the rollback CLI tool.",
            deliverables=[
                PlanningDeliverableDraft(
                    title="Rollback Mechanism", description="Core rollback logic."
                )
            ],
        ),
    )  # PLANNING -> ARCHITECTURE

    _run_ai_stage(
        platform,
        provider,
        proj.id,
        WorkflowStage.ARCHITECTURE,
        ArchitectureProposalDraft(design_summary="Command-based rollback engine."),
    )  # ARCHITECTURE -> REVIEW

    _run_ai_stage(
        platform,
        provider,
        proj.id,
        WorkflowStage.REVIEW,
        EvaluationProposalDraft(
            synthesis="Meets spec with one advisory finding.",
            findings=[
                EvaluationFindingDraft(
                    title="Missing rollback test",
                    summary="Add coverage for partial rollback failure.",
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.QUALITY,
                )
            ],
        ),
    )  # REVIEW -> ITERATION

    status = platform.get_workflow_status(GetWorkflowStatusCommand(project_id=proj.id))
    assert status.current_stage == WorkflowStage.ITERATION
    assert status.objectives  # DEFAULT_STAGE_OBJECTIVES for ITERATION
    assert status.is_ready_for_transition is False

    # Before RC-001: nothing reachable from the public facade could clear
    # these objectives, so the workflow was stuck here permanently.
    for objective in list(status.objectives):
        status = platform.complete_objective(
            CompleteObjectiveCommand(project_id=proj.id, objective=objective)
        )

    assert status.is_ready_for_transition is True
    assert status.objectives == []

    # ITERATION -> COMPLETION
    final = platform.transition_stage(TransitionStageCommand(project_id=proj.id))
    assert final.current_stage == WorkflowStage.COMPLETION
    assert final.objectives  # COMPLETION also has default objectives to clear

    for objective in list(final.objectives):
        final = platform.complete_objective(
            CompleteObjectiveCommand(project_id=proj.id, objective=objective)
        )
    assert final.is_ready_for_transition is True


def test_complete_objective_rejects_unknown_objective(platform: Atlas) -> None:
    """Completing a string that isn't an active objective must fail loudly,
    not silently no-op and leave the caller thinking it worked."""
    proj = platform.create_project(
        CreateProjectCommand(name="RC-001", description="D", objective="O")
    )

    with pytest.raises(ApplicationError):
        platform.complete_objective(
            CompleteObjectiveCommand(
                project_id=proj.id, objective="not a real objective"
            )
        )
