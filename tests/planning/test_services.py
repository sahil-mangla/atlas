from pathlib import Path
from uuid import UUID, uuid4

import pytest

from engine.domain.enums import PlanningStatus, ResearchStatus
from engine.domain.research import (
    ProblemDefinition,
    Research,
    ResearchSnapshot,
    ResearchSummary,
)
from engine.planning.exceptions import (
    InvalidPlanningOperationException,
)
from engine.planning.fs_repository import FilesystemPlanningRepository
from engine.planning.services import (
    DependencyPlanningService,
    MilestonePlanningService,
    PlanningInitializationService,
    PlanningSummaryService,
    ScopePlanningService,
    TaskPlanningService,
)
from engine.research.fs_repository import FilesystemResearchRepository


@pytest.fixture
def repos(
    tmp_path: Path,
) -> tuple[FilesystemPlanningRepository, FilesystemResearchRepository]:
    return (
        FilesystemPlanningRepository(tmp_path),
        FilesystemResearchRepository(tmp_path),
    )


def create_snapshot(snapshot_id: UUID) -> ResearchSnapshot:
    return ResearchSnapshot(
        id=snapshot_id,
        version=1,
        problem_definition=ProblemDefinition(statement="A", objectives=[]),
        research_sources=[],
        evidence=[],
        findings=[],
        constraints=[],
        assumptions=[],
        opportunities=[],
        open_questions=[],
        summary=ResearchSummary(synthesis="B", key_takeaways=[]),
        confidence=1.0,
    )


def test_initialization_service(
    repos: tuple[FilesystemPlanningRepository, FilesystemResearchRepository]
) -> None:
    plan_repo, res_repo = repos
    project_id = uuid4()
    research_snapshot_id = uuid4()

    # Need to setup research with snapshot
    snapshot = create_snapshot(research_snapshot_id)
    research = Research(
        project_id=project_id,
        status=ResearchStatus.APPROVED,
        snapshots=[snapshot],
    )
    res_repo.save(research)

    init_svc = PlanningInitializationService(plan_repo, res_repo)

    planning = init_svc.initialize_planning(project_id, research_snapshot_id)
    assert planning.project_id == project_id
    assert planning.status == PlanningStatus.DRAFT

    # Should raise error if already initialized
    with pytest.raises(InvalidPlanningOperationException):
        init_svc.initialize_planning(project_id, research_snapshot_id)


def test_scope_service(
    repos: tuple[FilesystemPlanningRepository, FilesystemResearchRepository]
) -> None:
    plan_repo, res_repo = repos
    project_id = uuid4()
    research_snapshot_id = uuid4()

    # Setup
    snapshot = create_snapshot(research_snapshot_id)
    res_repo.save(Research(project_id=project_id, snapshots=[snapshot]))
    init_svc = PlanningInitializationService(plan_repo, res_repo)
    init_svc.initialize_planning(project_id, research_snapshot_id)

    scope_svc = ScopePlanningService(plan_repo)
    scope = scope_svc.set_scope(
        project_id,
        "Statement",
        [{"title": "D1", "description": "Desc 1"}],
    )
    assert scope.statement == "Statement"
    assert len(scope.deliverables) == 1
    assert scope.deliverables[0].title == "D1"


def test_milestone_and_task_service(
    repos: tuple[FilesystemPlanningRepository, FilesystemResearchRepository]
) -> None:
    plan_repo, res_repo = repos
    project_id = uuid4()
    research_snapshot_id = uuid4()

    # Setup
    snapshot = create_snapshot(research_snapshot_id)
    res_repo.save(Research(project_id=project_id, snapshots=[snapshot]))
    PlanningInitializationService(plan_repo, res_repo).initialize_planning(
        project_id, research_snapshot_id
    )

    mile_svc = MilestonePlanningService(plan_repo)
    task_svc = TaskPlanningService(plan_repo)

    m = mile_svc.add_milestone(project_id, "M1")
    e = mile_svc.add_epic(project_id, m.id, "E1")
    t = task_svc.add_task(project_id, e.id, "T1", "Desc", ["AC1"], ["DoD1"])
    st = task_svc.add_subtask(project_id, t.id, "ST1", "Desc", ["AC2"], ["DoD2"])

    assert t.acceptance_criteria.criteria == ["AC1"]
    assert st.definition_of_done.standards == ["DoD2"]

    # Test Deletion
    task_svc.delete_task(project_id, t.id)
    planning = plan_repo.get_by_project_id(project_id)
    assert planning is not None
    assert len(planning.milestones[0].epics[0].tasks) == 0

    mile_svc.delete_milestone(project_id, m.id)
    planning = plan_repo.get_by_project_id(project_id)
    assert planning is not None
    assert len(planning.milestones) == 0


def test_dependency_service_cycle_detection(
    repos: tuple[FilesystemPlanningRepository, FilesystemResearchRepository]
) -> None:
    plan_repo, res_repo = repos
    project_id = uuid4()
    research_snapshot_id = uuid4()

    # Setup
    snapshot = create_snapshot(research_snapshot_id)
    res_repo.save(Research(project_id=project_id, snapshots=[snapshot]))
    PlanningInitializationService(plan_repo, res_repo).initialize_planning(
        project_id, research_snapshot_id
    )

    mile_svc = MilestonePlanningService(plan_repo)
    task_svc = TaskPlanningService(plan_repo)
    dep_svc = DependencyPlanningService(plan_repo)

    m = mile_svc.add_milestone(project_id, "M1")
    e = mile_svc.add_epic(project_id, m.id, "E1")
    t1 = task_svc.add_task(project_id, e.id, "T1")
    t2 = task_svc.add_task(project_id, e.id, "T2")
    t3 = task_svc.add_task(project_id, e.id, "T3")

    # t2 depends on t1
    dep_svc.add_dependency(project_id, t2.id, t1.id)
    # t3 depends on t2
    dep_svc.add_dependency(project_id, t3.id, t2.id)

    # Cycle: t1 depends on t3
    with pytest.raises(InvalidPlanningOperationException) as exc:
        dep_svc.add_dependency(project_id, t1.id, t3.id)
    assert "cycle" in str(exc.value).lower()


def test_summary_service(
    repos: tuple[FilesystemPlanningRepository, FilesystemResearchRepository]
) -> None:
    plan_repo, res_repo = repos
    project_id = uuid4()
    research_snapshot_id = uuid4()

    # Setup
    snapshot = create_snapshot(research_snapshot_id)
    res_repo.save(Research(project_id=project_id, snapshots=[snapshot]))
    PlanningInitializationService(plan_repo, res_repo).initialize_planning(
        project_id, research_snapshot_id
    )

    scope_svc = ScopePlanningService(plan_repo)
    sum_svc = PlanningSummaryService(plan_repo)

    scope_svc.set_scope(project_id, "Scope", [])

    sum_svc.submit_for_review(project_id)
    planning = plan_repo.get_by_project_id(project_id)
    assert planning is not None
    assert planning.status == PlanningStatus.REVIEW

    snap = sum_svc.freeze_snapshot(project_id, research_snapshot_id, "Synthesis")
    assert snap.version == 1
    assert snap.research_snapshot_id == research_snapshot_id

    planning = plan_repo.get_by_project_id(project_id)
    assert planning is not None
    assert planning.status == PlanningStatus.APPROVED
    assert len(planning.snapshots) == 1
