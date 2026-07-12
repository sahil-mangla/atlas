from uuid import UUID, uuid4

from engine.domain.enums import PlanningStatus, TaskStatus
from engine.domain.planning import (
    AcceptanceCriteria,
    DefinitionOfDone,
    EngineeringDeliverable,
    Planning,
    PlanningEpic,
    PlanningMilestone,
    PlanningSnapshot,
    PlanningSubtask,
    PlanningSummary,
    PlanningTask,
    ScopeDefinition,
)


def test_planning_models() -> None:
    deliv = EngineeringDeliverable(title="API", description="REST API")
    assert isinstance(deliv.id, UUID)

    scope = ScopeDefinition(statement="Build API", deliverables=[deliv])
    assert scope.statement == "Build API"
    assert len(scope.deliverables) == 1

    subtask = PlanningSubtask(
        title="Write test",
        acceptance_criteria=AcceptanceCriteria(criteria=["Passes"]),
        definition_of_done=DefinitionOfDone(standards=["Linted"]),
    )
    assert subtask.status == TaskStatus.PENDING

    task = PlanningTask(title="Build endpoint", subtasks=[subtask])
    assert len(task.subtasks) == 1

    epic = PlanningEpic(title="Auth Epic", tasks=[task])
    assert len(epic.tasks) == 1

    milestone = PlanningMilestone(title="v1", epics=[epic])
    assert len(milestone.epics) == 1

    summary = PlanningSummary(synthesis="Done", total_milestones=1, total_tasks=1)

    snapshot = PlanningSnapshot(
        version=1,
        research_snapshot_id=uuid4(),
        scope_definition=scope,
        milestones=[milestone],
        summary=summary,
    )
    assert snapshot.metadata.version == 1

    planning = Planning(project_id=uuid4())
    assert planning.status == PlanningStatus.DRAFT
    assert planning.scope_definition is None
    assert planning.snapshots == []
