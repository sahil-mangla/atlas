from unittest.mock import Mock
from uuid import uuid4

from atlas import Atlas
from atlas._service import _AtlasServices
from atlas.commands import ReviewKnowledgeCandidateCommand
from engine.domain.enums import KnowledgeActorType, ProposalDecision
from engine.domain.knowledge import KnowledgeActor
from engine.workflow.orchestration import WorkflowOrchestrationService


def test_review_knowledge_candidate_command_approve() -> None:
    orch = Mock(spec=WorkflowOrchestrationService)
    services = _AtlasServices(
        project_creation_service=Mock(),
        project_loading_service=Mock(),
        project_listing_service=Mock(),
        project_archive_service=Mock(),
        workflow_initialization_service=Mock(),
        workflow_repo=Mock(),
        workflow_transition_service=Mock(),
        orchestration_service=orch,
        proposal_repo=Mock(),
    )
    atlas = Atlas(services)

    cmd = ReviewKnowledgeCandidateCommand(
        project_id=uuid4(),
        candidate_id=uuid4(),
        decision=ProposalDecision.APPROVE,
        actor=KnowledgeActor(
            actor_type=KnowledgeActorType.HUMAN,
            actor_id="user",
            display_name="User",
        ),
    )

    atlas.review_knowledge_candidate(cmd)
    orch.process_knowledge_review.assert_called_once_with(
        cmd.project_id,
        cmd.candidate_id,
        cmd.decision,
        cmd.actor,
        cmd.feedback,
    )


def test_review_knowledge_candidate_command_reject() -> None:
    orch = Mock(spec=WorkflowOrchestrationService)
    services = _AtlasServices(
        project_creation_service=Mock(),
        project_loading_service=Mock(),
        project_listing_service=Mock(),
        project_archive_service=Mock(),
        workflow_initialization_service=Mock(),
        workflow_repo=Mock(),
        workflow_transition_service=Mock(),
        orchestration_service=orch,
        proposal_repo=Mock(),
    )
    atlas = Atlas(services)

    cmd = ReviewKnowledgeCandidateCommand(
        project_id=uuid4(),
        candidate_id=uuid4(),
        decision=ProposalDecision.REJECT,
        actor=KnowledgeActor(
            actor_type=KnowledgeActorType.HUMAN,
            actor_id="user",
            display_name="User",
        ),
        feedback="No thanks",
    )

    atlas.review_knowledge_candidate(cmd)
    orch.process_knowledge_review.assert_called_once_with(
        cmd.project_id,
        cmd.candidate_id,
        cmd.decision,
        cmd.actor,
        cmd.feedback,
    )
