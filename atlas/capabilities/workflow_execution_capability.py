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
from engine.project.repository import ProjectRepository
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowException,
    WorkflowNotFoundException,
)
from engine.workflow.orchestration import WorkflowOrchestrationService
from engine.workflow.repository import WorkflowRepository
from shared.state_snapshot import DirectoryStateSnapshot


class WorkflowExecutionCapability:
    """AI stage execution (proposal generation) and proposal review decisions."""

    def __init__(
        self,
        workflow_repo: WorkflowRepository,
        orchestration_service: WorkflowOrchestrationService,
        proposal_repo: ProposalRepository,
        project_repo: ProjectRepository | None = None,
    ) -> None:
        self._workflow_repo = workflow_repo
        self._orchestration_service = orchestration_service
        self._proposal_repo = proposal_repo
        # Optional: without it approvals still work but are not rolled back
        # as a whole when a late write fails.
        self._project_repo = project_repo
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
                raise InvalidTransitionException(
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

        # Approval writes the stage aggregate, the workflow, extracted
        # knowledge, the project record and the proposal record in turn. Only
        # the first is covered by the commit's own rollback, so capture the
        # project's state and put it all back if any later step fails;
        # otherwise the project is left half-approved and cannot be retried.
        snapshot = self._capture_project_state(command.project_id)
        original_status = proposal.status
        try:
            result = self._approve(command, proposal)
        except Exception as error:
            proposal.status = original_status
            self._pending_proposals[command.proposal_id] = record
            self._roll_back(snapshot, error)
            if isinstance(error, ApplicationError):
                raise
            raise StageExecutionError(
                f"Approval failed and was rolled back; nothing was changed. "
                f"Cause: {error}"
            ) from error
        if not result.success:
            proposal.status = original_status
            self._roll_back(snapshot, None)
        return result

    def _capture_project_state(self, project_id: UUID) -> DirectoryStateSnapshot | None:
        if self._project_repo is None:
            return None
        project_path = self._project_repo.get_project_path(project_id)
        return DirectoryStateSnapshot(
            (project_path / ".atlas", project_path / "atlas-proposals")
        )

    @staticmethod
    def _roll_back(
        snapshot: DirectoryStateSnapshot | None, cause: Exception | None
    ) -> None:
        if snapshot is None:
            return
        try:
            snapshot.restore()
        except OSError as restore_error:
            raise StageExecutionError(
                "Approval failed and could not be fully rolled back "
                f"({restore_error}); the project may be partly updated. "
                f"Original cause: {cause or 'commit failed'}"
            ) from restore_error

    def _approve(
        self, command: ApproveProposalCommand, proposal: AIProposal[Any]
    ) -> AppCommitResult:
        try:
            commit_res = self._orchestration_service.process_review_decision(
                project_id=command.project_id,
                proposal=proposal,
                decision=ProposalDecision.APPROVE,
                approver=command.actor,
            )
            if commit_res:
                if commit_res.success:
                    patch_summary = (
                        f"Snapshot {commit_res.committed_snapshot_id} committed."
                    )
                else:
                    # Surface the actual validation/rollback errors instead of a
                    # bare "Snapshot None committed." with no actionable detail.
                    patch_summary = "Commit failed: " + (
                        "; ".join(commit_res.errors) or "unknown error."
                    )
                result = AppCommitResult(
                    success=commit_res.success,
                    proposal_id=command.proposal_id,
                    patch_summary=patch_summary,
                    transition_blocked=commit_res.transition_blocked,
                    blocking_issues=tuple(commit_res.errors)
                    + tuple(commit_res.transition_errors),
                )
                if result.success:
                    self._pending_proposals.pop(command.proposal_id, None)
                    # Re-render the record so the archived copy says
                    # "approved" rather than the "draft" it was written as.
                    self._proposal_repo.save(command.project_id, proposal)
                    self._proposal_repo.archive_approved(command.proposal_id)
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
