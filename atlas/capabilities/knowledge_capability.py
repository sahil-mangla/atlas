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

from atlas.commands import ReviewKnowledgeCandidateCommand
from atlas.exceptions import (
    ApplicationError,
    InvalidTransitionError,
    KnowledgeReviewError,
    WorkflowNotReadyError,
)
from atlas.results import OperationResult
from engine.knowledge.exceptions import KnowledgeException
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowException,
    WorkflowNotFoundException,
)
from engine.workflow.orchestration import WorkflowOrchestrationService


class KnowledgeCapability:
    """Human review of pending knowledge candidates."""

    def __init__(self, orchestration_service: WorkflowOrchestrationService) -> None:
        self._orchestration_service = orchestration_service

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

    def review_knowledge_candidate(
        self, command: ReviewKnowledgeCandidateCommand
    ) -> OperationResult:
        """Apply a human review decision to one pending knowledge candidate."""
        try:
            self._orchestration_service.process_knowledge_review(
                command.project_id,
                command.candidate_id,
                command.decision,
                command.actor,
                command.feedback,
            )
            return OperationResult(
                success=True, message="Knowledge candidate reviewed."
            )
        except WorkflowException as exc:
            raise self._map_workflow_exception(exc) from exc
        except KnowledgeException as exc:
            raise self._map_knowledge_exception(exc) from exc
