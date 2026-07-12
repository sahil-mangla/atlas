from uuid import UUID, uuid4

from engine.domain.enums import Priority, TaskStatus
from engine.domain.roadmap import Milestone, Roadmap, Task


def test_task_construction() -> None:
    spec_id = uuid4()
    dep_id = uuid4()
    task = Task(
        title="Setup Db",
        description="Initialize database",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.HIGH,
        dependencies=[dep_id],
        specification_id=spec_id,
    )
    assert isinstance(task.id, UUID)
    assert task.title == "Setup Db"
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.priority == Priority.HIGH
    assert task.dependencies == [dep_id]
    assert task.specification_id == spec_id


def test_milestone_construction() -> None:
    task = Task(title="Setup Db")
    milestone = Milestone(
        title="Milestone 1",
        description="First milestone",
        tasks=[task],
    )
    assert isinstance(milestone.id, UUID)
    assert milestone.title == "Milestone 1"
    assert len(milestone.tasks) == 1
    assert milestone.tasks[0].title == "Setup Db"


def test_roadmap_defaults() -> None:
    project_id = uuid4()
    roadmap = Roadmap(project_id=project_id)
    assert isinstance(roadmap.id, UUID)
    assert roadmap.project_id == project_id
    assert roadmap.milestones == []
    assert roadmap.progress == 0.0


def test_roadmap_custom() -> None:
    roadmap_id = uuid4()
    project_id = uuid4()
    task = Task(title="Setup Db")
    milestone = Milestone(title="Milestone 1", tasks=[task])

    expected_progress = 45.5
    roadmap = Roadmap(
        id=roadmap_id,
        project_id=project_id,
        milestones=[milestone],
        progress=expected_progress,
    )

    assert roadmap.id == roadmap_id
    assert roadmap.project_id == project_id
    assert len(roadmap.milestones) == 1
    assert roadmap.progress == expected_progress
