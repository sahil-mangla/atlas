"""Serialization logic for the ATLAS Workflow System."""

from datetime import datetime
from typing import Any

from engine.domain.enums import ApprovalStatus, ProposalDecision, WorkflowStage
from engine.domain.workflow import ProposalReviewEntry, Workflow, WorkflowHistoryEntry


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


def serialize_proposal_review(entry: ProposalReviewEntry) -> dict[str, Any]:
    """Serialize a durable proposal-review record."""
    return {
        "proposal_id": str(entry.proposal_id),
        "approver": entry.approver,
        "decision": entry.decision.value,
        "timestamp": entry.timestamp.isoformat(),
        "comment": entry.comment,
    }


def deserialize_proposal_review(data: dict[str, Any]) -> ProposalReviewEntry:
    """Deserialize a durable proposal-review record."""
    return ProposalReviewEntry(
        proposal_id=data["proposal_id"],
        approver=data["approver"],
        decision=ProposalDecision(data["decision"]),
        timestamp=datetime.fromisoformat(data["timestamp"]),
        comment=data.get("comment"),
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
        "proposal_reviews": [
            serialize_proposal_review(entry) for entry in workflow.proposal_reviews
        ],
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
        proposal_reviews=[
            deserialize_proposal_review(entry)
            for entry in data.get("proposal_reviews", [])
        ],
    )
