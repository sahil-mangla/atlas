from datetime import datetime
from uuid import UUID, uuid4

from engine.domain.enums import ProjectStatus, WorkflowStage
from engine.domain.project import Project


def test_project_defaults() -> None:
    project = Project(
        name="ATLAS Project",
        description="ATLAS description",
        objective="ATLAS objective",
    )
    assert isinstance(project.id, UUID)
    assert project.name == "ATLAS Project"
    assert project.description == "ATLAS description"
    assert project.objective == "ATLAS objective"
    assert project.status == ProjectStatus.INITIALIZED
    assert project.current_stage == WorkflowStage.IDEA
    assert project.workspace_id is None
    assert project.roadmap_id is None
    assert project.architecture_id is None
    assert project.research_id is None
    assert project.memory_id is None
    assert project.workflow_id is None
    assert project.evaluation_ids == []
    assert isinstance(project.created_at, datetime)
    assert isinstance(project.updated_at, datetime)


def test_project_custom_values() -> None:
    proj_id = uuid4()
    workspace_id = uuid4()
    roadmap_id = uuid4()
    architecture_id = uuid4()
    research_id = uuid4()
    memory_id = uuid4()
    workflow_id = uuid4()
    eval_id = uuid4()

    project = Project(
        id=proj_id,
        name="Custom ATLAS",
        description="Custom description",
        objective="Custom objective",
        status=ProjectStatus.ACTIVE,
        current_stage=WorkflowStage.IMPLEMENTATION,
        workspace_id=workspace_id,
        roadmap_id=roadmap_id,
        architecture_id=architecture_id,
        research_id=research_id,
        memory_id=memory_id,
        workflow_id=workflow_id,
        evaluation_ids=[eval_id],
    )

    assert project.id == proj_id
    assert project.name == "Custom ATLAS"
    assert project.status == ProjectStatus.ACTIVE
    assert project.current_stage == WorkflowStage.IMPLEMENTATION
    assert project.workspace_id == workspace_id
    assert project.roadmap_id == roadmap_id
    assert project.architecture_id == architecture_id
    assert project.research_id == research_id
    assert project.memory_id == memory_id
    assert project.workflow_id == workflow_id
    assert project.evaluation_ids == [eval_id]


def test_project_serialization() -> None:
    project = Project(
        name="ATLAS Project",
        description="ATLAS description",
        objective="ATLAS objective",
    )
    dumped = project.model_dump()
    assert dumped["name"] == "ATLAS Project"
    assert dumped["status"] == "initialized"

    loaded = Project(**dumped)
    assert loaded.id == project.id
    assert loaded.name == project.name
