"""AI proposal generation, approval, and rejection capability.

Relocated verbatim from ``atlas/_service.py``'s pre-Phase-15 ``Atlas``
methods. Named ``WorkflowExecutionCapability`` -- not a generic "execution"
concept -- because its scope is intentionally narrow: AI stage execution
(proposal generation) and the two proposal review decisions, nothing else.
This is a thin delegation layer -- see the Capability Responsibility Rule in
``docs/plans/phase-15-platform-layer.md`` §3.5.
"""

from typing import Any
from uuid import UUID

from atlas.commands import (
    ApproveProposalCommand,
    ExecuteStageCommand,
    RejectProposalCommand,
)
from atlas.exceptions import (
    AIProviderError,
    ApplicationError,
    ContextAssemblyError,
    InvalidTransitionError,
    ProposalValidationError,
    StageExecutionError,
    WorkflowNotReadyError,
)
from atlas.results import CommitResult as AppCommitResult
from atlas.results import OperationResult, ProposalResult
from atlas.types import ProposalStatus
from engine.ai.exceptions import (
    AIException,
    AIProviderException,
    InvalidContextException,
    InvalidProposalException,
)
from engine.ai.repository import ProposalRepository
from engine.domain.ai import AIProposal
from engine.domain.ai_feedback import ProposalFeedback
from engine.domain.enums import ProposalDecision
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowException,
    WorkflowNotFoundException,
)
from engine.workflow.orchestration import WorkflowOrchestrationService
from engine.workflow.repository import WorkflowRepository


class WorkflowExecutionCapability:
    """AI stage execution (proposal generation) and proposal review decisions."""

    def __init__(
        self,
        workflow_repo: WorkflowRepository,
        orchestration_service: WorkflowOrchestrationService,
        proposal_repo: ProposalRepository,
    ) -> None:
        self._workflow_repo = workflow_repo
        self._orchestration_service = orchestration_service
        self._proposal_repo = proposal_repo
        # Proposal cache is bounded by removal after review completion.
        self._pending_proposals: dict[UUID, tuple[UUID, AIProposal[Any]]] = {}

    def _map_ai_exception(self, e: Exception) -> ApplicationError:
        """Map internal AI exceptions to application errors."""
        if isinstance(e, AIProviderException):
            return AIProviderError(str(e))
        if isinstance(e, InvalidContextException):
            return ContextAssemblyError(str(e))
        if isinstance(e, InvalidProposalException):
            return ProposalValidationError(str(e))
        if isinstance(e, AIException):
            return StageExecutionError(str(e))
        raise e

    def _map_workflow_exception(self, e: Exception) -> ApplicationError:
        """Map internal workflow exceptions to application errors.

        Restored to full parity with the pre-Phase-15 shared
        ``Atlas._map_workflow_exception`` (audit finding): this capability's
        earlier version dropped the ``InvalidTransitionException`` branch --
        currently dormant for this capability's own call sites, but a latent
        fidelity gap against the original method this was relocated from.
        """
        if isinstance(e, WorkflowNotFoundException):
            return WorkflowNotReadyError(str(e))
        if isinstance(e, InvalidTransitionException):
            return InvalidTransitionError(str(e))
        if isinstance(e, WorkflowException):
            return ApplicationError(str(e))
        raise e

    def execute_stage(self, command: ExecuteStageCommand) -> ProposalResult:
        """Execute a workflow stage with AI generation."""
        try:
            workflow = self._workflow_repo.get_by_project_id(command.project_id)
            if not workflow:
                raise WorkflowNotFoundException(
                    f"Workflow for project {command.project_id} not found."
                )
            if workflow.current_stage.value != command.stage.value:
                raise InvalidTransitionError(
                    "Requested stage does not match the active workflow stage."
                )
            proposal = self._orchestration_service.generate_proposal(
                project_id=command.project_id, user_instructions=""
            )
            self._proposal_repo.save(command.project_id, proposal)
            self._pending_proposals[proposal.id] = (command.project_id, proposal)
            return ProposalResult(
                id=proposal.id,
                project_id=command.project_id,
                stage=command.stage,
                status=ProposalStatus(proposal.status.value),
                content=proposal.data.model_dump()
                if hasattr(proposal.data, "model_dump")
                else proposal.data,
            )
        except AIException as e:
            raise self._map_ai_exception(e) from e
        except WorkflowException as e:
            raise self._map_workflow_exception(e) from e

    def approve_proposal(self, command: ApproveProposalCommand) -> AppCommitResult:
        """Approve a generated AI proposal."""
        record = self._pending_proposals.get(command.proposal_id)
        if not record:
            record = self._proposal_repo.get_by_id(command.proposal_id)
        if not record:
            raise ProposalValidationError(
                f"Proposal {command.proposal_id} not found or expired."
            )
        proposal_project_id, proposal = record
        if proposal_project_id != command.project_id:
            raise ProposalValidationError(
                "Proposal does not belong to the requested project."
            )

        try:
            commit_res = self._orchestration_service.process_review_decision(
                project_id=command.project_id,
                proposal=proposal,
                decision=ProposalDecision.APPROVE,
                approver=command.actor,
            )
            if commit_res:
                result = AppCommitResult(
                    success=commit_res.success,
                    proposal_id=command.proposal_id,
                    patch_summary=(
                        f"Snapshot {commit_res.committed_snapshot_id} committed."
                    ),
                )
                if result.success:
                    self._pending_proposals.pop(command.proposal_id, None)
                    self._proposal_repo.delete(command.proposal_id)
                return result
            return AppCommitResult(
                success=False,
                proposal_id=command.proposal_id,
                patch_summary="Commit failed.",
            )
        except AIException as e:
            raise self._map_ai_exception(e) from e
        except WorkflowException as e:
            raise self._map_workflow_exception(e) from e

    def reject_proposal(self, command: RejectProposalCommand) -> OperationResult:
        """Reject a generated AI proposal with feedback."""
        record = self._pending_proposals.get(command.proposal_id)
        if not record:
            record = self._proposal_repo.get_by_id(command.proposal_id)
        if not record:
            raise ProposalValidationError(
                f"Proposal {command.proposal_id} not found or expired."
            )
        proposal_project_id, proposal = record
        if proposal_project_id != command.project_id:
            raise ProposalValidationError(
                "Proposal does not belong to the requested project."
            )

        try:
            feedback = ProposalFeedback(
                feedback=command.feedback,
                proposal_id=command.proposal_id,
                author=command.actor,
            )
            self._orchestration_service.process_review_decision(
                project_id=command.project_id,
                proposal=proposal,
                decision=ProposalDecision.REJECT,
                feedback=feedback,
                approver="Client Adapter",
            )
            self._pending_proposals.pop(command.proposal_id, None)
            self._proposal_repo.delete(command.proposal_id)
            return OperationResult(success=True, message="Proposal rejected.")
        except AIException as e:
            raise self._map_ai_exception(e) from e
        except WorkflowException as e:
            raise self._map_workflow_exception(e) from e
