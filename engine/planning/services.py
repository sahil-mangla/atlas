"""Services for managing the Planning lifecycle."""

from uuid import UUID

from engine.domain.enums import PlanningStatus
from engine.domain.metadata import ArtifactMetadata, ArtifactStatus
from engine.domain.planning import (
    AcceptanceCriteria,
    DefinitionOfDone,
    EngineeringDeliverable,
    Planning,
    PlanningEpic,
    PlanningMilestone,
    PlanningSnapshot,
    PlanningSubtask,
    PlanningSummary,
    PlanningTask,
    ScopeDefinition,
)
from engine.planning.exceptions import (
    InvalidPlanningOperationException,
    PlanningNotFoundException,
)
from engine.planning.repository import PlanningRepository
from engine.research.repository import ResearchRepository


class PlanningInitializationService:
    """Handles creating the initial planning state for a project."""

    def __init__(
        self, planning_repo: PlanningRepository, research_repo: ResearchRepository
    ) -> None:
        self.planning_repo = planning_repo
        self.research_repo = research_repo

    def initialize_planning(
        self, project_id: UUID, research_snapshot_id: UUID
    ) -> Planning:
        """Create a new planning context for a project based on approved research."""
        if self.planning_repo.exists(project_id):
            raise InvalidPlanningOperationException(
                f"Planning already exists for project {project_id}."
            )

        research = self.research_repo.get_by_project_id(project_id)
        if not research:
            raise InvalidPlanningOperationException("Project research not found.")

        # Ensure the specified snapshot exists (meaning it was approved)
        snapshot_exists = any(
            s.metadata.id == research_snapshot_id for s in research.snapshots
        )
        if not snapshot_exists:
            raise InvalidPlanningOperationException(
                "Specified research snapshot not found or not approved."
            )

        planning = Planning(project_id=project_id, status=PlanningStatus.DRAFT)
        self.planning_repo.save(planning)
        return planning


def _ensure_mutable(planning: Planning) -> None:
    """Ensure the planning aggregate is in DRAFT or REVIEW state."""
    if planning.status in (PlanningStatus.APPROVED, PlanningStatus.ARCHIVED):
        raise InvalidPlanningOperationException(
            "Cannot mutate planning that is APPROVED or ARCHIVED."
        )


def _ensure_draft(planning: Planning) -> None:
    """Ensure the planning aggregate is in DRAFT state."""
    if planning.status != PlanningStatus.DRAFT:
        raise InvalidPlanningOperationException(
            "Deletion is only allowed while Planning is in DRAFT state."
        )


class ScopePlanningService:
    """Handles setting the scope and engineering deliverables."""

    def __init__(self, repository: PlanningRepository) -> None:
        self.repository = repository

    def set_scope(
        self,
        project_id: UUID,
        statement: str,
        deliverables: list[dict[str, str]],
    ) -> ScopeDefinition:
        """Set the active scope definition."""
        planning = self.repository.get_by_project_id(project_id)
        if not planning:
            raise PlanningNotFoundException()
        _ensure_mutable(planning)

        eng_deliverables = [
            EngineeringDeliverable(title=d["title"], description=d.get("description", ""))
            for d in deliverables
        ]
        scope = ScopeDefinition(statement=statement, deliverables=eng_deliverables)
        planning.scope_definition = scope
        self.repository.save(planning)
        return scope


class MilestonePlanningService:
    """Handles managing milestones and epics."""

    def __init__(self, repository: PlanningRepository) -> None:
        self.repository = repository

    def add_milestone(
        self, project_id: UUID, title: str, description: str = ""
    ) -> PlanningMilestone:
        planning = self.repository.get_by_project_id(project_id)
        if not planning:
            raise PlanningNotFoundException()
        _ensure_mutable(planning)

        milestone = PlanningMilestone(title=title, description=description)
        planning.milestones.append(milestone)
        self.repository.save(planning)
        return milestone

    def add_epic(
        self, project_id: UUID, milestone_id: UUID, title: str, description: str = ""
    ) -> PlanningEpic:
        planning = self.repository.get_by_project_id(project_id)
        if not planning:
            raise PlanningNotFoundException()
        _ensure_mutable(planning)

        epic = PlanningEpic(title=title, description=description)
        for m in planning.milestones:
            if m.id == milestone_id:
                m.epics.append(epic)
                self.repository.save(planning)
                return epic

        raise InvalidPlanningOperationException("Milestone not found.")

    def delete_milestone(self, project_id: UUID, milestone_id: UUID) -> None:
        planning = self.repository.get_by_project_id(project_id)
        if not planning:
            raise PlanningNotFoundException()
        _ensure_draft(planning)

        original_count = len(planning.milestones)
        planning.milestones = [m for m in planning.milestones if m.id != milestone_id]
        if len(planning.milestones) == original_count:
            raise InvalidPlanningOperationException("Milestone not found.")
        self.repository.save(planning)


class TaskPlanningService:
    """Handles managing tasks and subtasks."""

    def __init__(self, repository: PlanningRepository) -> None:
        self.repository = repository

    def add_task(
        self,
        project_id: UUID,
        epic_id: UUID,
        title: str,
        description: str = "",
        acceptance_criteria: list[str] | None = None,
        definition_of_done: list[str] | None = None,
    ) -> PlanningTask:
        planning = self.repository.get_by_project_id(project_id)
        if not planning:
            raise PlanningNotFoundException()
        _ensure_mutable(planning)

        ac = AcceptanceCriteria(criteria=acceptance_criteria or [])
        dod = DefinitionOfDone(standards=definition_of_done or [])
        task = PlanningTask(
            title=title,
            description=description,
            acceptance_criteria=ac,
            definition_of_done=dod,
        )

        for m in planning.milestones:
            for e in m.epics:
                if e.id == epic_id:
                    e.tasks.append(task)
                    self.repository.save(planning)
                    return task

        raise InvalidPlanningOperationException("Epic not found.")

    def add_subtask(
        self,
        project_id: UUID,
        task_id: UUID,
        title: str,
        description: str = "",
        acceptance_criteria: list[str] | None = None,
        definition_of_done: list[str] | None = None,
    ) -> PlanningSubtask:
        planning = self.repository.get_by_project_id(project_id)
        if not planning:
            raise PlanningNotFoundException()
        _ensure_mutable(planning)

        ac = AcceptanceCriteria(criteria=acceptance_criteria or [])
        dod = DefinitionOfDone(standards=definition_of_done or [])
        subtask = PlanningSubtask(
            title=title,
            description=description,
            acceptance_criteria=ac,
            definition_of_done=dod,
        )

        for m in planning.milestones:
            for e in m.epics:
                for t in e.tasks:
                    if t.id == task_id:
                        t.subtasks.append(subtask)
                        self.repository.save(planning)
                        return subtask

        raise InvalidPlanningOperationException("Task not found.")

    def delete_task(self, project_id: UUID, task_id: UUID) -> None:
        planning = self.repository.get_by_project_id(project_id)
        if not planning:
            raise PlanningNotFoundException()
        _ensure_draft(planning)

        found = False
        for m in planning.milestones:
            for e in m.epics:
                original_count = len(e.tasks)
                e.tasks = [t for t in e.tasks if t.id != task_id]
                if len(e.tasks) < original_count:
                    found = True
                    break
            if found:
                break

        if not found:
            raise InvalidPlanningOperationException("Task not found.")
        self.repository.save(planning)


class DependencyPlanningService:
    """Handles task and subtask dependencies and cycle validation."""

    def __init__(self, repository: PlanningRepository) -> None:
        self.repository = repository

    def _validate_no_cycles(self, planning: Planning) -> None:
        graph: dict[UUID, list[UUID]] = {}
        for m in planning.milestones:
            for e in m.epics:
                for t in e.tasks:
                    graph[t.id] = t.dependencies
                    for st in t.subtasks:
                        graph[st.id] = st.dependencies

        visited: set[UUID] = set()
        rec_stack: set[UUID] = set()

        def dfs(node: UUID) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited and dfs(node):
                raise InvalidPlanningOperationException(
                    "Dependency cycle detected in the roadmap."
                )

    def add_dependency(
        self, project_id: UUID, item_id: UUID, depends_on_id: UUID
    ) -> None:
        """Add a dependency from one task/subtask to another."""
        planning = self.repository.get_by_project_id(project_id)
        if not planning:
            raise PlanningNotFoundException()
        _ensure_mutable(planning)

        if item_id == depends_on_id:
            raise InvalidPlanningOperationException("Item cannot depend on itself.")

        found = False
        for m in planning.milestones:
            for e in m.epics:
                for t in e.tasks:
                    if t.id == item_id:
                        t.dependencies.append(depends_on_id)
                        found = True
                    for st in t.subtasks:
                        if st.id == item_id:
                            st.dependencies.append(depends_on_id)
                            found = True

        if not found:
            raise InvalidPlanningOperationException("Dependent item not found.")

        # Ensure that depends_on_id actually exists in the graph globally
        all_ids = {
            t.id
            for m in planning.milestones
            for e in m.epics
            for t in e.tasks
        }
        all_ids.update(
            st.id
            for m in planning.milestones
            for e in m.epics
            for t in e.tasks
            for st in t.subtasks
        )
        if depends_on_id not in all_ids:
            raise InvalidPlanningOperationException("Dependency target not found.")

        self._validate_no_cycles(planning)
        self.repository.save(planning)


class PlanningSummaryService:
    """Handles synthesizing and finalizing planning snapshots."""

    def __init__(self, repository: PlanningRepository) -> None:
        self.repository = repository

    def submit_for_review(self, project_id: UUID) -> Planning:
        """Transition planning state from DRAFT to REVIEW."""
        planning = self.repository.get_by_project_id(project_id)
        if not planning:
            raise PlanningNotFoundException()
        if planning.status != PlanningStatus.DRAFT:
            raise InvalidPlanningOperationException("Only DRAFT can enter REVIEW.")

        planning.status = PlanningStatus.REVIEW
        self.repository.save(planning)
        return planning

    def freeze_snapshot(
        self, project_id: UUID, research_snapshot_id: UUID, synthesis: str
    ) -> PlanningSnapshot:
        """Create an immutable snapshot of the active planning state."""
        planning = self.repository.get_by_project_id(project_id)
        if not planning:
            raise PlanningNotFoundException()
        if not planning.scope_definition:
            raise InvalidPlanningOperationException(
                "Cannot freeze without a scope definition."
            )

        total_tasks = sum(
            len(e.tasks) for m in planning.milestones for e in m.epics
        )
        summary = PlanningSummary(
            synthesis=synthesis,
            total_milestones=len(planning.milestones),
            total_tasks=total_tasks,
        )

        next_version = len(planning.snapshots) + 1
        snapshot = PlanningSnapshot(
            metadata=ArtifactMetadata(
                version=next_version,
                status=ArtifactStatus.APPROVED,
            ),
            research_snapshot_id=research_snapshot_id,
            scope_definition=planning.scope_definition,
            milestones=list(planning.milestones),
            summary=summary,
        )

        planning.summary = summary
        planning.snapshots.append(snapshot)
        planning.status = PlanningStatus.APPROVED
        self.repository.save(planning)
        return snapshot
