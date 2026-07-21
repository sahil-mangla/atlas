"""Service layer for the ATLAS Workflow System."""

from typing import ClassVar
from uuid import UUID

from engine.domain.enums import ApprovalStatus, EvaluationStatus, WorkflowStage
from engine.domain.workflow import ReadinessReview, Workflow, WorkflowHistoryEntry
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowNotFoundException,
)
from engine.workflow.repository import WorkflowRepository

# Default objectives defined for each engineering stage
DEFAULT_STAGE_OBJECTIVES: dict[WorkflowStage, list[str]] = {
    WorkflowStage.IDEA: [
        "Define project boundaries",
        "Outline concept overview",
    ],
    WorkflowStage.RESEARCH: [
        "Review literature",
        "Identify knowledge gaps",
        "Synthesize findings",
    ],
    WorkflowStage.PROBLEM_DEFINITION: [
        "Document requirements",
        "Establish scoping limits",
        "Lock requirements",
    ],
    WorkflowStage.PLANNING: [
        "Define milestones",
        "Schedule task roadmap",
        "Map dependencies",
    ],
    WorkflowStage.ARCHITECTURE: [
        "Create design blueprints",
        "Draft API contracts",
        "Record ADRs",
    ],
    WorkflowStage.IMPLEMENTATION: [
        "Execute code modifications",
        "Verify build success",
    ],
    WorkflowStage.REVIEW: [
        "Verify against specifications",
        "Pass architectural audits",
    ],
    WorkflowStage.ITERATION: [
        "Address review feedback",
        "Resolve blocking bugs",
    ],
    WorkflowStage.COMPLETION: [
        "Finalize documentation",
        "Archive milestone",
    ],
}


class WorkflowInitializationService:
    """Service to initialize a project's workflow state."""

    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    def initialize_workflow(self, project_id: UUID) -> Workflow:
        """Initialize the workflow state for a new project.

        Starts the project at the IDEA stage with no active objectives: the
        IDEA objectives ("Define project boundaries", "Outline concept
        overview") are already satisfied by the description/objective the
        caller supplies at project creation (see
        ``ProjectCreationService.create_project``), so IDEA is auto-ready to
        transition to RESEARCH rather than requiring a manual checklist step.

        Args:
            project_id: The UUID of the project.

        Returns:
            The initialized Workflow domain model.
        """
        workflow = Workflow(
            project_id=project_id,
            current_stage=WorkflowStage.IDEA,
            completed_stages=[],
            pending_stages=list(WorkflowStage)[1:],
            active_objectives=[],
            history=[],
        )
        self.repository.save(workflow)
        return workflow


class WorkflowProgressService:
    """Service to manage active objectives and progress within a stage."""

    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    def set_active_objectives(
        self, project_id: UUID, objectives: list[str]
    ) -> Workflow:
        """Explicitly set the active objectives for the current stage.

        Args:
            project_id: The UUID of the project.
            objectives: The new list of active objectives.

        Returns:
            The updated Workflow.
        """
        workflow = self.repository.get_by_project_id(project_id)
        if not workflow:
            raise WorkflowNotFoundException(
                f"Workflow for project {project_id} not found."
            )

        workflow.active_objectives = objectives
        self.repository.save(workflow)
        return workflow

    def complete_objective(self, project_id: UUID, objective: str) -> Workflow:
        """Mark an active objective as completed by removing it from the list.

        Args:
            project_id: The UUID of the project.
            objective: The objective string to complete.

        Returns:
            The updated Workflow.
        """
        workflow = self.repository.get_by_project_id(project_id)
        if not workflow:
            raise WorkflowNotFoundException(
                f"Workflow for project {project_id} not found."
            )

        if objective in workflow.active_objectives:
            workflow.active_objectives.remove(objective)
            self.repository.save(workflow)
        return workflow


class WorkflowReadinessService:
    """Service to evaluate workflow stage readiness.

    This service is ONLY responsible for evaluating readiness and generating a
    ReadinessReview. It never decides if a transition is valid and never
    transitions stages.
    """

    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    def evaluate_readiness(self, project_id: UUID) -> ReadinessReview:
        """Evaluate the readiness of the project's current stage.

        Args:
            project_id: The UUID of the project.

        Returns:
            A ReadinessReview representing the evaluation outcome.
        """
        workflow = self.repository.get_by_project_id(project_id)
        if not workflow:
            raise WorkflowNotFoundException(
                f"Workflow for project {project_id} not found."
            )

        # If there are active objectives outstanding, readiness has failed
        if workflow.active_objectives:
            status = EvaluationStatus.FAILED
            blocking = list(workflow.active_objectives)
            completed = []
        else:
            status = EvaluationStatus.PASSED
            blocking = []
            completed = list(DEFAULT_STAGE_OBJECTIVES.get(workflow.current_stage, []))

        # Simple heuristics for optional improvements
        improvements = []
        if workflow.current_stage == WorkflowStage.RESEARCH:
            improvements.append("Verify all cited papers are accessible offline.")

        return ReadinessReview(
            stage=workflow.current_stage,
            status=status,
            completed_objectives=completed,
            blocking_issues=blocking,
            optional_improvements=improvements,
            confidence=1.0 if not blocking else 0.5,
        )


class WorkflowTransitionService:
    """Service to validate and execute workflow stage transitions.

    This service is ONLY responsible for transition validation and executing
    transitions. It enforces the Human Approval Principle and does not evaluate
    readiness directly.
    """

    # Define the valid transitions in the state machine
    VALID_TRANSITIONS: ClassVar[dict[WorkflowStage, set[WorkflowStage]]] = {
        WorkflowStage.IDEA: {WorkflowStage.RESEARCH},
        # PLANNING and REVIEW are also direct, legal targets from RESEARCH and
        # ARCHITECTURE respectively: PROBLEM_DEFINITION and IMPLEMENTATION have
        # no AI-generation support (no StageExecutor is registered for either),
        # so they are optional manual detours rather than mandatory waypoints.
        WorkflowStage.RESEARCH: {
            WorkflowStage.PROBLEM_DEFINITION,
            WorkflowStage.PLANNING,
            WorkflowStage.IDEA,
        },
        WorkflowStage.PROBLEM_DEFINITION: {
            WorkflowStage.PLANNING,
            WorkflowStage.RESEARCH,
        },
        WorkflowStage.PLANNING: {
            WorkflowStage.ARCHITECTURE,
            WorkflowStage.PROBLEM_DEFINITION,
        },
        WorkflowStage.ARCHITECTURE: {
            WorkflowStage.IMPLEMENTATION,
            WorkflowStage.REVIEW,
            WorkflowStage.PLANNING,
        },
        WorkflowStage.IMPLEMENTATION: {
            WorkflowStage.REVIEW,
            WorkflowStage.ARCHITECTURE,
        },
        WorkflowStage.REVIEW: {
            WorkflowStage.ITERATION,
            WorkflowStage.COMPLETION,
            WorkflowStage.IMPLEMENTATION,
        },
        WorkflowStage.ITERATION: {
            WorkflowStage.COMPLETION,
            WorkflowStage.REVIEW,
            WorkflowStage.IMPLEMENTATION,
        },
        WorkflowStage.COMPLETION: {WorkflowStage.ITERATION},
    }

    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    def transition_stage(
        self,
        project_id: UUID,
        new_stage: WorkflowStage,
        approval_status: ApprovalStatus,
        reason: str,
        confidence: float = 1.0,
    ) -> Workflow:
        """Validate and execute a stage transition.

        Args:
            project_id: The UUID of the project.
            new_stage: The target WorkflowStage.
            approval_status: The human approval status.
            reason: The reason or justification for the transition.
            confidence: The transition confidence score.

        Returns:
            The transitioned Workflow.

        Raises:
            WorkflowNotFoundException: If the workflow state doesn't exist.
            InvalidTransitionException: If transition is invalid or unapproved.
        """
        workflow = self.repository.get_by_project_id(project_id)
        if not workflow:
            raise WorkflowNotFoundException(
                f"Workflow for project {project_id} not found."
            )

        # 1. State machine validation
        current = workflow.current_stage
        allowed = self.VALID_TRANSITIONS.get(current, set())
        if new_stage not in allowed:
            raise InvalidTransitionException(
                f"Transition from {current} to {new_stage} is illegal."
            )

        # 2. Human approval verification
        if approval_status != ApprovalStatus.APPROVED:
            raise InvalidTransitionException(
                f"Cannot execute transition without explicit approval. "
                f"Current status: {approval_status}"
            )

        # 3. Apply the transition
        entry = WorkflowHistoryEntry(
            previous_stage=current,
            new_stage=new_stage,
            approval_status=approval_status,
            reason=reason,
            confidence=confidence,
        )
        workflow.record_transition(entry)

        # Set default objectives for the new stage
        workflow.active_objectives = list(DEFAULT_STAGE_OBJECTIVES.get(new_stage, []))

        self.repository.save(workflow)
        return workflow


class WorkflowHistoryService:
    """Service to inspect and retrieve the immutable transition history."""

    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    def get_history(self, project_id: UUID) -> list[WorkflowHistoryEntry]:
        """Retrieve all transition history entries for a project.

        Args:
            project_id: The UUID of the project.

        Returns:
            A list of WorkflowHistoryEntry instances.
        """
        workflow = self.repository.get_by_project_id(project_id)
        if not workflow:
            raise WorkflowNotFoundException(
                f"Workflow for project {project_id} not found."
            )

        # Return history copy to preserve immutability
        return list(workflow.history)
