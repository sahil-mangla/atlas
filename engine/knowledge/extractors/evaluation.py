from datetime import UTC, datetime
from uuid import UUID, uuid4

from engine.domain.enums import (
    FindingSeverity,
    KnowledgeActorType,
    KnowledgeCategory,
    KnowledgeSourceType,
)
from engine.domain.knowledge import (
    KnowledgeActor,
    KnowledgeCandidate,
    KnowledgeProvenance,
)
from engine.evaluation.repository import EvaluationRepository
from engine.knowledge.extractors.base import KnowledgeExtractor


class EvaluationKnowledgeExtractor(KnowledgeExtractor):
    def __init__(self, evaluation_repo: EvaluationRepository) -> None:
        self.evaluation_repo = evaluation_repo

    @property
    def source_type(self) -> KnowledgeSourceType:
        return KnowledgeSourceType.EVALUATION_SNAPSHOT

    def extract(self, project_id: UUID, source_id: UUID) -> list[KnowledgeCandidate]:
        evaluation = self.evaluation_repo.get_by_project_id(project_id)
        if not evaluation:
            return []
        snapshot = next((s for s in evaluation.snapshots if s.metadata.id == source_id), None)
        if not snapshot:
            return []

        candidates = []
        now = datetime.now(UTC)
        actor = KnowledgeActor(
            actor_type=KnowledgeActorType.SYSTEM,
            actor_id="evaluation_extractor",
            display_name="Evaluation Extractor",
        )
        provenance = KnowledgeProvenance(
            source_type=self.source_type,
            source_id=source_id,
            source_description=f"Evaluation Snapshot {source_id}",
            extracted_at=now,
            actor=actor,
        )

        candidates.append(
            KnowledgeCandidate(
                id=uuid4(),
                project_id=project_id,
                title="Evaluation Synthesis",
                content=snapshot.summary.synthesis,
                category=KnowledgeCategory.LESSON_LEARNED,
                rationale="Extracted from evaluation synthesis",
                provenance=provenance,
                author=actor,
                created_at=now,
            )
        )

        for finding in snapshot.findings:
            if finding.severity == FindingSeverity.BLOCKING:
                candidates.append(
                    KnowledgeCandidate(
                        id=uuid4(),
                        project_id=project_id,
                        title=f"Blocking Finding: {finding.category.value}",
                        content=finding.description,
                        category=KnowledgeCategory.LESSON_LEARNED,
                        rationale="Extracted from evaluation blocking finding",
                        provenance=provenance,
                        author=actor,
                        created_at=now,
                    )
                )

        return candidates
