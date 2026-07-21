from datetime import UTC, datetime
from uuid import UUID, uuid4

from engine.architecture.repository import ArchitectureRepository
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


class ArchitectureKnowledgeExtractor(KnowledgeExtractor):
    def __init__(self, architecture_repo: ArchitectureRepository) -> None:
        self.architecture_repo = architecture_repo

    @property
    def source_type(self) -> KnowledgeSourceType:
        return KnowledgeSourceType.ARCHITECTURE_SNAPSHOT

    def extract(self, project_id: UUID, source_id: UUID) -> list[KnowledgeCandidate]:
        architecture = self.architecture_repo.get_by_project_id(project_id)
        if not architecture:
            return []
        snapshot = next(
            (s for s in architecture.snapshots if s.metadata.id == source_id), None
        )
        if not snapshot:
            return []

        candidates = []
        now = datetime.now(UTC)
        actor = KnowledgeActor(
            actor_type=KnowledgeActorType.SYSTEM,
            actor_id="architecture_extractor",
            display_name="Architecture Extractor",
        )
        provenance = KnowledgeProvenance(
            source_type=self.source_type,
            source_id=source_id,
            source_description=f"Architecture Snapshot {source_id}",
            extracted_at=now,
            actor=actor,
        )

        candidates.append(
            KnowledgeCandidate(
                id=uuid4(),
                project_id=project_id,
                title="Technical Design Summary",
                content=snapshot.summary.synthesis,
                category=KnowledgeCategory.DECISION_SUMMARY,
                rationale="Extracted from architecture design summary",
                provenance=provenance,
                author=actor,
                created_at=now,
            )
        )

        for decision in snapshot.decisions:
            candidates.append(
                KnowledgeCandidate(
                    id=uuid4(),
                    project_id=project_id,
                    title=f"ADR: {decision.title}",
                    content=(
                        f"**Context:** {decision.context}\n\n"
                        f"**Decision:** {decision.decision}\n\n"
                        f"**Consequences:** {decision.consequences}"
                    ),
                    category=KnowledgeCategory.DECISION_SUMMARY,
                    rationale="Extracted from architecture decision (ADR)",
                    provenance=provenance,
                    author=actor,
                    created_at=now,
                )
            )

        for component in snapshot.components:
            candidates.append(
                KnowledgeCandidate(
                    id=uuid4(),
                    project_id=project_id,
                    title=f"Component: {component.name}",
                    content="**Responsibilities:**\n"
                    + "\n".join(f"- {r}" for r in component.responsibilities),
                    category=KnowledgeCategory.PATTERN,
                    rationale="Extracted from architecture component",
                    provenance=provenance,
                    author=actor,
                    created_at=now,
                )
            )

        return candidates
