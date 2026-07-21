"""Unit tests for the workflow serializers."""

from uuid import uuid4

from engine.domain.enums import ApprovalStatus, ProposalDecision, WorkflowStage
from engine.domain.workflow import ProposalReviewEntry, Workflow, WorkflowHistoryEntry
from engine.workflow.serializers import (
    deserialize_history_entry,
    deserialize_workflow,
    serialize_history_entry,
    serialize_workflow,
)


def test_serialize_and_deserialize_history_entry() -> None:
    entry = WorkflowHistoryEntry(
        previous_stage=WorkflowStage.IDEA,
        new_stage=WorkflowStage.RESEARCH,
        approval_status=ApprovalStatus.APPROVED,
        reason="Looks good",
        confidence=0.9,
    )

    data = serialize_history_entry(entry)

    assert data["previous_stage"] == "idea"
    assert data["new_stage"] == "research"
    assert data["approval_status"] == "approved"
    assert data["reason"] == "Looks good"
    assert data["confidence"] == 0.9

    deserialized = deserialize_history_entry(data)

    assert deserialized.id == entry.id
    assert deserialized.previous_stage == entry.previous_stage
    assert deserialized.new_stage == entry.new_stage
    assert deserialized.approval_status == entry.approval_status
    assert deserialized.reason == entry.reason
    assert deserialized.confidence == entry.confidence
    assert deserialized.timestamp == entry.timestamp


def test_serialize_and_deserialize_workflow() -> None:
    workflow = Workflow(project_id=uuid4())
    entry = WorkflowHistoryEntry(
        previous_stage=WorkflowStage.IDEA,
        new_stage=WorkflowStage.RESEARCH,
        approval_status=ApprovalStatus.APPROVED,
        reason="Good",
        confidence=1.0,
    )
    workflow.record_transition(entry)
    review = ProposalReviewEntry(
        proposal_id=uuid4(),
        approver="principal.engineer",
        decision=ProposalDecision.APPROVE,
        comment="Approved for commit.",
    )
    workflow.record_proposal_review(review)

    data = serialize_workflow(workflow)

    assert data["id"] == str(workflow.id)
    assert data["current_stage"] == "research"
    assert len(data["history"]) == 1
    assert data["proposal_reviews"][0]["approver"] == "principal.engineer"

    deserialized = deserialize_workflow(data)

    assert deserialized.id == workflow.id
    assert deserialized.project_id == workflow.project_id
    assert deserialized.current_stage == workflow.current_stage
    assert len(deserialized.history) == 1
    assert deserialized.history[0].id == entry.id
    assert deserialized.proposal_reviews == [review]
