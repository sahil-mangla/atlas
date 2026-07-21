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
from engine.research.repository import ResearchRepository


class ResearchKnowledgeExtractor(KnowledgeExtractor):
    def __init__(self, research_repo: ResearchRepository) -> None:
        self.research_repo = research_repo

    @property
    def source_type(self) -> KnowledgeSourceType:
        return KnowledgeSourceType.RESEARCH_SNAPSHOT

    def extract(self, project_id: UUID, source_id: UUID) -> list[KnowledgeCandidate]:
        research = self.research_repo.get_by_project_id(project_id)
        if not research:
            return []
        snapshot = next(
            (s for s in research.snapshots if s.metadata.id == source_id), None
        )
        if not snapshot:
            return []

        candidates = []
        now = datetime.now(UTC)
        actor = KnowledgeActor(
            actor_type=KnowledgeActorType.SYSTEM,
            actor_id="research_extractor",
            display_name="Research Extractor",
        )
        provenance = KnowledgeProvenance(
            source_type=self.source_type,
            source_id=source_id,
            source_description=f"Research Snapshot {source_id}",
            extracted_at=now,
            actor=actor,
        )

        for finding in snapshot.findings:
            candidates.append(
                KnowledgeCandidate(
                    id=uuid4(),
                    project_id=project_id,
                    title=finding.title,
                    content=finding.summary,
                    category=KnowledgeCategory.LESSON_LEARNED,
                    rationale="Extracted from research finding",
                    provenance=provenance,
                    author=actor,
                    created_at=now,
                )
            )

        for constraint in snapshot.constraints:
            candidates.append(
                KnowledgeCandidate(
                    id=uuid4(),
                    project_id=project_id,
                    title=f"Constraint: {constraint.description[:50]}...",
                    content=f"{constraint.description}\n\nImpact: {constraint.impact}",
                    category=KnowledgeCategory.CONSTRAINT,
                    rationale="Extracted from research constraint",
                    provenance=provenance,
                    author=actor,
                    created_at=now,
                )
            )

        for assumption in snapshot.assumptions:
            candidates.append(
                KnowledgeCandidate(
                    id=uuid4(),
                    project_id=project_id,
                    title=f"Assumption: {assumption.description[:50]}...",
                    content=f"{assumption.description}\n\nRisk: {assumption.risk}",
                    category=KnowledgeCategory.LESSON_LEARNED,
                    rationale="Extracted from research assumption",
                    provenance=provenance,
                    author=actor,
                    created_at=now,
                )
            )

        return candidates
