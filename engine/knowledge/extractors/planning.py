from datetime import UTC, datetime
from uuid import UUID, uuid4

from engine.domain.enums import (
    KnowledgeActorType,
    KnowledgeCategory,
    KnowledgeSourceType,
)
from engine.domain.knowledge import (
    KnowledgeActor,
    KnowledgeCandidate,
    KnowledgeProvenance,
)
from engine.knowledge.extractors.base import KnowledgeExtractor
from engine.planning.repository import PlanningRepository


class PlanningKnowledgeExtractor(KnowledgeExtractor):
    def __init__(self, planning_repo: PlanningRepository) -> None:
        self.planning_repo = planning_repo

    @property
    def source_type(self) -> KnowledgeSourceType:
        return KnowledgeSourceType.PLANNING_SNAPSHOT

    def extract(self, project_id: UUID, source_id: UUID) -> list[KnowledgeCandidate]:
        planning = self.planning_repo.get_by_project_id(project_id)
        if not planning:
            return []
        snapshot = next((s for s in planning.snapshots if s.metadata.id == source_id), None)
        if not snapshot:
            return []

        candidates = []
        now = datetime.now(UTC)
        actor = KnowledgeActor(
            actor_type=KnowledgeActorType.SYSTEM,
            actor_id="planning_extractor",
            display_name="Planning Extractor",
        )
        provenance = KnowledgeProvenance(
            source_type=self.source_type,
            source_id=source_id,
            source_description=f"Planning Snapshot {source_id}",
            extracted_at=now,
            actor=actor,
        )

        candidates.append(
            KnowledgeCandidate(
                id=uuid4(),
                project_id=project_id,
                title="Project Scope Statement",
                content=snapshot.scope_definition.statement,
                category=KnowledgeCategory.DECISION_SUMMARY,
                rationale="Extracted from planning scope statement",
                provenance=provenance,
                author=actor,
                created_at=now,
            )
        )

        for milestone in snapshot.milestones:
            candidates.append(
                KnowledgeCandidate(
                    id=uuid4(),
                    project_id=project_id,
                    title=f"Milestone: {milestone.title}",
                    content=milestone.description,
                    category=KnowledgeCategory.PATTERN,
                    rationale="Extracted from planning milestone",
                    provenance=provenance,
                    author=actor,
                    created_at=now,
                )
            )

        return candidates
