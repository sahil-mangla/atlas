"""Knowledge candidate human-review capability.

Relocated verbatim from ``atlas/_service.py``'s pre-Phase-15
``Atlas.review_knowledge_candidate``. This is a thin delegation layer --
see the Capability Responsibility Rule in
``docs/plans/phase-15-platform-layer.md`` §3.5.

Note: ``get_knowledge_read_model`` is owned by ``PresentationCapability``,
not this class -- in the current codebase it lives in the same "Phase 14
typed read models" grouping as ``get_project_read_model`` et al., sourced
directly from repositories, while this capability owns only the human
review *action* (a command handler, like ``execute_stage`` or
``approve_proposal``).
"""

from atlas.commands import (
    KnowledgeActorInput,
    ListKnowledgeCandidatesCommand,
    ReviewKnowledgeCandidateCommand,
    ShowKnowledgeCandidateCommand,
)
from atlas.exceptions import (
    ApplicationError,
    InvalidTransitionError,
    KnowledgeReviewError,
    WorkflowNotReadyError,
)
from atlas.results import (
    KnowledgeCandidateListResult,
    KnowledgeCandidateResult,
    OperationResult,
)
from atlas.types import KnowledgeCandidateStatus as AtlasKnowledgeCandidateStatus
from atlas.types import ProposalDecision as AtlasProposalDecision
from engine.domain.enums import KnowledgeActorType as EngineKnowledgeActorType
from engine.domain.enums import (
    KnowledgeCandidateStatus as EngineKnowledgeCandidateStatus,
)
from engine.domain.enums import ProposalDecision as EngineProposalDecision
from engine.domain.knowledge import KnowledgeActor as EngineKnowledgeActor
from engine.domain.knowledge import KnowledgeCandidate
from engine.knowledge.exceptions import KnowledgeException
from engine.knowledge.orchestration import KnowledgeOrchestrationService
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowException,
    WorkflowNotFoundException,
)
from engine.workflow.orchestration import WorkflowOrchestrationService


def _to_result(candidate: KnowledgeCandidate) -> KnowledgeCandidateResult:
    return KnowledgeCandidateResult(
        id=candidate.id,
        project_id=candidate.project_id,
        title=candidate.title,
        content=candidate.content,
        category=candidate.category.value,
        tags=tuple(candidate.tags),
        status=candidate.status.value,
        rationale=candidate.rationale,
        review_comment=candidate.review_comment,
        created_at=candidate.created_at,
    )


def _to_engine_status(
    status: AtlasKnowledgeCandidateStatus | None,
) -> EngineKnowledgeCandidateStatus | None:
    return EngineKnowledgeCandidateStatus(status.value) if status else None


def _to_engine_decision(decision: AtlasProposalDecision) -> EngineProposalDecision:
    return EngineProposalDecision(decision.value)


def _to_engine_actor(actor: KnowledgeActorInput) -> EngineKnowledgeActor:
    return EngineKnowledgeActor(
        actor_type=EngineKnowledgeActorType(actor.actor_type.value),
        actor_id=actor.actor_id,
        display_name=actor.display_name,
    )


class KnowledgeCapability:
    """Listing and human review of engineering-knowledge candidates."""

    def __init__(self, orchestration_service: WorkflowOrchestrationService) -> None:
        self._orchestration_service = orchestration_service

    def _knowledge_orchestration(self) -> KnowledgeOrchestrationService:
        knowledge_orchestration = self._orchestration_service.knowledge_orchestration
        if not knowledge_orchestration:
            raise ApplicationError("Knowledge subsystem is not configured.")
        return knowledge_orchestration

    def _map_workflow_exception(self, e: Exception) -> ApplicationError:
        """Map internal workflow exceptions to application errors.

        Duplicated from WorkflowCapability rather than shared, matching the
        "no cross-capability coupling" rule the other capabilities already
        follow (see PresentationCapability._map_project_exception).
        """
        if isinstance(e, WorkflowNotFoundException):
            return WorkflowNotReadyError(str(e))
        if isinstance(e, InvalidTransitionException):
            return InvalidTransitionError(str(e))
        if isinstance(e, WorkflowException):
            return ApplicationError(str(e))
        raise e

    def _map_knowledge_exception(self, e: Exception) -> ApplicationError:
        """Map internal knowledge exceptions to application errors."""
        if isinstance(e, KnowledgeException):
            return KnowledgeReviewError(str(e))
        raise e

    def list_candidates(
        self, command: ListKnowledgeCandidatesCommand
    ) -> KnowledgeCandidateListResult:
        """List a project's engineering-knowledge candidates."""
        candidates = self._knowledge_orchestration().list_candidates(
            command.project_id, _to_engine_status(command.status)
        )
        return KnowledgeCandidateListResult(
            candidates=[_to_result(c) for c in candidates]
        )

    def show_candidate(
        self, command: ShowKnowledgeCandidateCommand
    ) -> KnowledgeCandidateResult:
        """Show a single engineering-knowledge candidate's full detail."""
        candidate = self._knowledge_orchestration().get_candidate(
            command.project_id, command.candidate_id
        )
        if not candidate:
            raise KnowledgeReviewError(
                f"Knowledge candidate {command.candidate_id} not found."
            )
        return _to_result(candidate)

    def review_knowledge_candidate(
        self, command: ReviewKnowledgeCandidateCommand
    ) -> OperationResult:
        """Apply a human review decision to one pending knowledge candidate."""
        try:
            self._orchestration_service.process_knowledge_review(
                command.project_id,
                command.candidate_id,
                _to_engine_decision(command.decision),
                _to_engine_actor(command.actor),
                command.feedback,
            )
            return OperationResult(
                success=True, message="Knowledge candidate reviewed."
            )
        except WorkflowException as exc:
            raise self._map_workflow_exception(exc) from exc
        except KnowledgeException as exc:
            raise self._map_knowledge_exception(exc) from exc
