"""Serialization logic for the ATLAS Workflow System."""

from datetime import datetime
from typing import Any

from engine.domain.enums import ApprovalStatus, WorkflowStage
from engine.domain.workflow import Workflow, WorkflowHistoryEntry


def serialize_history_entry(entry: WorkflowHistoryEntry) -> dict[str, Any]:
    """Serialize a WorkflowHistoryEntry into a dictionary."""
    return {
        "id": str(entry.id),
        "previous_stage": entry.previous_stage.value if entry.previous_stage else None,
        "new_stage": entry.new_stage.value,
        "timestamp": entry.timestamp.isoformat(),
        "approval_status": entry.approval_status.value,
        "reason": entry.reason,
        "confidence": entry.confidence,
    }


def deserialize_history_entry(data: dict[str, Any]) -> WorkflowHistoryEntry:
    """Deserialize a dictionary into a WorkflowHistoryEntry."""
    prev_stage = data.get("previous_stage")
    return WorkflowHistoryEntry(
        id=data["id"],
        previous_stage=WorkflowStage(prev_stage) if prev_stage else None,
        new_stage=WorkflowStage(data["new_stage"]),
        timestamp=datetime.fromisoformat(data["timestamp"]),
        approval_status=ApprovalStatus(data["approval_status"]),
        reason=data["reason"],
        confidence=data.get("confidence", 1.0),
    )


def serialize_workflow(workflow: Workflow) -> dict[str, Any]:
    """Serialize a Workflow aggregate into a dictionary."""
    return {
        "id": str(workflow.id),
        "project_id": str(workflow.project_id),
        "current_stage": workflow.current_stage.value,
        "completed_stages": [s.value for s in workflow.completed_stages],
        "pending_stages": [s.value for s in workflow.pending_stages],
        "active_objectives": workflow.active_objectives,
        "history": [serialize_history_entry(e) for e in workflow.history],
    }


def deserialize_workflow(data: dict[str, Any]) -> Workflow:
    """Deserialize a dictionary into a Workflow aggregate."""
    return Workflow(
        id=data["id"],
        project_id=data["project_id"],
        current_stage=WorkflowStage(data["current_stage"]),
        completed_stages=[WorkflowStage(s) for s in data.get("completed_stages", [])],
        pending_stages=[WorkflowStage(s) for s in data.get("pending_stages", [])],
        active_objectives=data.get("active_objectives", []),
        history=[deserialize_history_entry(e) for e in data.get("history", [])],
    )
