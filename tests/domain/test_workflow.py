from uuid import UUID, uuid4

from engine.domain.enums import WorkflowStage
from engine.domain.workflow import Workflow


def test_workflow_defaults() -> None:
    project_id = uuid4()
    workflow = Workflow(project_id=project_id)

    assert isinstance(workflow.id, UUID)
    assert workflow.project_id == project_id
    assert workflow.current_stage == WorkflowStage.IDEA
    assert workflow.completed_stages == []
    assert workflow.pending_stages == []
    assert workflow.active_objectives == []


def test_workflow_custom() -> None:
    wf_id = uuid4()
    project_id = uuid4()

    workflow = Workflow(
        id=wf_id,
        project_id=project_id,
        current_stage=WorkflowStage.IMPLEMENTATION,
        completed_stages=[WorkflowStage.IDEA, WorkflowStage.PLANNING],
        pending_stages=[WorkflowStage.REVIEW, WorkflowStage.COMPLETION],
        active_objectives=["Write tests", "Format codebase"],
    )

    assert workflow.id == wf_id
    assert workflow.project_id == project_id
    assert workflow.current_stage == WorkflowStage.IMPLEMENTATION
    assert workflow.completed_stages == [WorkflowStage.IDEA, WorkflowStage.PLANNING]
    assert workflow.pending_stages == [WorkflowStage.REVIEW, WorkflowStage.COMPLETION]
    assert workflow.active_objectives == ["Write tests", "Format codebase"]
