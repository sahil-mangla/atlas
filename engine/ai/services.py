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
from engine.domain.metadata import ArtifactStatus
from engine.evaluation.repository import EvaluationRepository
from engine.memory.repository import MemoryRepository
from engine.planning.repository import PlanningRepository
from engine.prompt.registry import PromptRegistry
from engine.research.repository import ResearchRepository


class ContextAssemblerService:
    """Collect approved domain snapshots into an immutable context payload."""

    def __init__(
        self,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
        architecture_repo: ArchitectureRepository,
        evaluation_repo: EvaluationRepository,
        memory_repo: MemoryRepository,
    ) -> None:
        self.research_repo = research_repo
        self.planning_repo = planning_repo
        self.architecture_repo = architecture_repo
        self.evaluation_repo = evaluation_repo
        self.memory_repo = memory_repo

    def assemble_context(self, project_id: UUID) -> ContextPayload:
        """Query subsystems for their latest approved snapshots and serialize them."""
        research = self.research_repo.get_by_project_id(project_id)
        planning = self.planning_repo.get_by_project_id(project_id)
        architecture = self.architecture_repo.get_by_project_id(project_id)
        evaluation = self.evaluation_repo.get_by_project_id(project_id)

        def latest_approved(aggregate: Any, name: str) -> Any:
            snapshots = getattr(aggregate, "snapshots", []) if aggregate else []
            for snapshot in reversed(snapshots):
                if snapshot.metadata.status == ArtifactStatus.APPROVED:
                    return snapshot
            raise InvalidContextException(f"Approved {name} snapshot required.")

        research_snapshot = latest_approved(research, "research")
        planning_snapshot = latest_approved(planning, "planning")
        architecture_snapshot = latest_approved(architecture, "architecture")
        evaluation_snapshot = (
            latest_approved(evaluation, "evaluation") if evaluation else None
        )

        res_snap_id = research_snapshot.metadata.id
        plan_snap_id = planning_snapshot.metadata.id
        arch_snap_id = architecture_snapshot.metadata.id
        eval_snap_id = evaluation_snapshot.metadata.id if evaluation_snapshot else None

        # Serialize fixed sections so prompts remain readable and deterministic.
        serialized = (
            f"# Engineering Context\n\n## Project\n{project_id}\n\n"
            f"## Research\n{research_snapshot.model_dump_json(indent=2)}\n\n"
            f"## Planning\n{planning_snapshot.model_dump_json(indent=2)}\n\n"
            f"## Architecture\n{architecture_snapshot.model_dump_json(indent=2)}\n\n"
            "## Evaluation\n"
            f"{self._serialize_snapshot(evaluation_snapshot)}\n\n"
            "## Engineering Memory\nNone\n"
        )

        return ContextPayload(
            research_snapshot_id=res_snap_id,
            planning_snapshot_id=plan_snap_id,
            architecture_snapshot_id=arch_snap_id,
            evaluation_snapshot_id=eval_snap_id,
            memory_entries=[],
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
