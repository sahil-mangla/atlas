"""AI Orchestration and Context Assembly services.

These services enforce the strict boundary between AI generation and
domain state mutation.
"""

from typing import Any
from uuid import UUID

from engine.ai.exceptions import InvalidContextException
from engine.ai.executor import PromptExecutor
from engine.architecture.repository import ArchitectureRepository
from engine.domain.ai import ContextPayload
from engine.domain.enums import WorkflowStage
from engine.domain.knowledge import EngineeringKnowledgeContext
from engine.domain.metadata import ArtifactStatus
from engine.evaluation.repository import EvaluationRepository
from engine.memory.repository import MemoryRepository
from engine.planning.repository import PlanningRepository
from engine.project.repository import ProjectRepository
from engine.prompt.registry import PromptRegistry
from engine.research.repository import ResearchRepository

#: Subsystems that must already carry an approved snapshot before a given
#: stage's proposal can be generated. Earlier stages have fewer (Research,
#: the first stage, has none); each stage otherwise only depends on the
#: stages upstream of it in the pipeline, never on itself or downstream ones.
_STAGE_PREREQUISITES: dict[WorkflowStage, tuple[str, ...]] = {
    WorkflowStage.RESEARCH: (),
    WorkflowStage.PLANNING: ("research",),
    WorkflowStage.ARCHITECTURE: ("research", "planning"),
    WorkflowStage.REVIEW: ("research", "planning", "architecture"),
}


class ContextAssemblerService:
    """Collect approved domain snapshots into an immutable context payload."""

    def __init__(  # noqa: PLR0913
        self,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
        architecture_repo: ArchitectureRepository,
        evaluation_repo: EvaluationRepository,
        memory_repo: MemoryRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self.research_repo = research_repo
        self.planning_repo = planning_repo
        self.architecture_repo = architecture_repo
        self.evaluation_repo = evaluation_repo
        self.memory_repo = memory_repo
        self.project_repo = project_repo

    def assemble_context(
        self,
        project_id: UUID,
        engineering_knowledge: EngineeringKnowledgeContext | None = None,
        stage: WorkflowStage | None = None,
    ) -> ContextPayload:
        """Query subsystems for their latest approved snapshots and serialize them.

        Only the subsystems that must precede ``stage`` in the pipeline are
        required to already carry an approved snapshot (e.g. Research has no
        prerequisites; Architecture requires Research and Planning). A
        snapshot for any other subsystem is included when available but never
        required -- otherwise generating the very first Research proposal on
        a fresh project would be impossible, since no snapshot exists yet.
        """
        research = self.research_repo.get_by_project_id(project_id)
        planning = self.planning_repo.get_by_project_id(project_id)
        architecture = self.architecture_repo.get_by_project_id(project_id)
        evaluation = self.evaluation_repo.get_by_project_id(project_id)
        required = _STAGE_PREREQUISITES.get(stage, ()) if stage else ()

        def latest_approved(aggregate: Any, name: str) -> Any:
            snapshots = getattr(aggregate, "snapshots", []) if aggregate else []
            for snapshot in reversed(snapshots):
                if snapshot.metadata.status == ArtifactStatus.APPROVED:
                    return snapshot
            if name in required:
                raise InvalidContextException(f"Approved {name} snapshot required.")
            return None

        research_snapshot = latest_approved(research, "research")
        planning_snapshot = latest_approved(planning, "planning")
        architecture_snapshot = latest_approved(architecture, "architecture")
        evaluation_snapshot = latest_approved(evaluation, "evaluation")

        res_snap_id = research_snapshot.metadata.id if research_snapshot else None
        plan_snap_id = planning_snapshot.metadata.id if planning_snapshot else None
        arch_snap_id = (
            architecture_snapshot.metadata.id if architecture_snapshot else None
        )
        eval_snap_id = evaluation_snapshot.metadata.id if evaluation_snapshot else None

        # Serialize fixed sections so prompts remain readable and deterministic.
        knowledge_section = (
            engineering_knowledge or EngineeringKnowledgeContext()
        ).serialized_section
        project = self.project_repo.get_by_id(project_id)
        project_definition = (
            f"Name: {project.name}\n"
            f"Description: {project.description}\n"
            f"Objective: {project.objective}"
            if project
            else "Unknown -- project record not found."
        )
        serialized = (
            f"# Engineering Context\n\n## Project\n{project_id}\n\n"
            f"## Project Definition\n{project_definition}\n\n"
            f"## Research\n{self._serialize_snapshot(research_snapshot)}\n\n"
            f"## Planning\n{self._serialize_snapshot(planning_snapshot)}\n\n"
            f"## Architecture\n{self._serialize_snapshot(architecture_snapshot)}\n\n"
            "## Evaluation\n"
            f"{self._serialize_snapshot(evaluation_snapshot)}\n\n"
            "## Engineering Memory\nNone\n\n"
            f"{knowledge_section}"
        )

        return ContextPayload(
            research_snapshot_id=res_snap_id,
            planning_snapshot_id=plan_snap_id,
            architecture_snapshot_id=arch_snap_id,
            evaluation_snapshot_id=eval_snap_id,
            memory_entries=(),
            knowledge_entry_ids=tuple(
                (engineering_knowledge or EngineeringKnowledgeContext()).entry_ids
            ),
            serialized_context=serialized,
        )

    @staticmethod
    def _serialize_snapshot(snapshot: Any | None) -> str:
        """Serialize an optional snapshot for a deterministic context section."""
        return snapshot.model_dump_json(indent=2) if snapshot else "None"


class AIOrchestrationService:
    """Expose the stateless prompt runtime to AI engineering services."""

    def __init__(
        self,
        prompt_executor: PromptExecutor,
        prompt_registry: PromptRegistry,
    ) -> None:
        self.prompt_executor = prompt_executor
        self.prompt_registry = prompt_registry
