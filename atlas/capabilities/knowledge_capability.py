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
from atlas.exceptions import ApplicationError
from atlas.results import OperationResult
from engine.knowledge.exceptions import KnowledgeException
from engine.workflow.exceptions import WorkflowException
from engine.workflow.orchestration import WorkflowOrchestrationService


class KnowledgeCapability:
    """Human review of pending knowledge candidates."""

    def __init__(self, orchestration_service: WorkflowOrchestrationService) -> None:
        self._orchestration_service = orchestration_service

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
        except (WorkflowException, KnowledgeException) as exc:
            raise ApplicationError(str(exc)) from exc
