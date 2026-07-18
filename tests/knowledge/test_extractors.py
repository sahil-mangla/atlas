# ruff: noqa: E501, PLR2004
from unittest.mock import Mock
from uuid import uuid4

from engine.architecture.repository import ArchitectureRepository
from engine.domain.architecture import (
    ArchitecturalDecision,
    Architecture,
    ArchitectureComponent,
    ArchitectureSnapshot,
    ArchitectureSummary,
)
from engine.domain.enums import FindingCategory, FindingSeverity, KnowledgeSourceType
from engine.domain.evaluation import (
    Evaluation,
    EvaluationFinding,
    EvaluationSnapshot,
    EvaluationSummary,
)
from engine.domain.knowledge import KnowledgeCandidate
from engine.domain.metadata import ArtifactMetadata
from engine.domain.planning import (
    Planning,
    PlanningMilestone,
    PlanningSnapshot,
    ScopeDefinition,
)
from engine.domain.research import (
    Assumption,
    Constraint,
    Research,
    ResearchFinding,
    ResearchSnapshot,
)
from engine.evaluation.repository import EvaluationRepository
from engine.knowledge.extractors.architecture import ArchitectureKnowledgeExtractor
from engine.knowledge.extractors.base import ExtractorRegistry
from engine.knowledge.extractors.evaluation import EvaluationKnowledgeExtractor
from engine.knowledge.extractors.planning import PlanningKnowledgeExtractor
from engine.knowledge.extractors.research import ResearchKnowledgeExtractor
from engine.planning.repository import PlanningRepository
from engine.research.repository import ResearchRepository


def test_research_extractor() -> None:
    repo = Mock(spec=ResearchRepository)
    project_id = uuid4()
    source_id = uuid4()
    snapshot = ResearchSnapshot.model_construct(
        metadata=ArtifactMetadata.model_construct(id=source_id),
        findings=[ResearchFinding.model_construct(title="F1", summary="F1 desc", evidence_ids=[uuid4()])],
        constraints=[Constraint.model_construct(description="C1", impact="high")],
        assumptions=[Assumption.model_construct(description="A1", risk="low")],
    )
    repo.get_by_project_id.return_value = Research.model_construct(snapshots=[snapshot])
    extractor = ResearchKnowledgeExtractor(repo)
    candidates = extractor.extract(project_id, source_id)
    assert len(candidates) == 3
    assert candidates[0].title == "F1"
    assert "C1" in candidates[1].title
    assert "A1" in candidates[2].title

def test_planning_extractor() -> None:
    repo = Mock(spec=PlanningRepository)
    project_id = uuid4()
    source_id = uuid4()
    snapshot = PlanningSnapshot.model_construct(
        metadata=ArtifactMetadata.model_construct(id=source_id),
        scope_definition=ScopeDefinition.model_construct(statement="Scope", deliverables=[]),
        milestones=[PlanningMilestone.model_construct(title="M1", description="M1 desc")],
    )
    repo.get_by_project_id.return_value = Planning.model_construct(snapshots=[snapshot])
    extractor = PlanningKnowledgeExtractor(repo)
    candidates = extractor.extract(project_id, source_id)
    assert len(candidates) == 2
    assert candidates[0].title == "Project Scope Statement"
    assert candidates[0].content == "Scope"
    assert candidates[1].title == "Milestone: M1"

def test_architecture_extractor() -> None:
    repo = Mock(spec=ArchitectureRepository)
    project_id = uuid4()
    source_id = uuid4()
    snapshot = ArchitectureSnapshot.model_construct(
        metadata=ArtifactMetadata.model_construct(id=source_id),
        summary=ArchitectureSummary.model_construct(synthesis="Design"),
        decisions=[ArchitecturalDecision.model_construct(title="ADR1", context="C", decision="D", consequences="C")],
        components=[ArchitectureComponent.model_construct(name="Comp1", responsibilities=["R1"])],
    )
    repo.get_by_project_id.return_value = Architecture.model_construct(snapshots=[snapshot])
    extractor = ArchitectureKnowledgeExtractor(repo)
    candidates = extractor.extract(project_id, source_id)
    assert len(candidates) == 3
    assert candidates[0].title == "Technical Design Summary"
    assert candidates[0].content == "Design"
    assert "ADR1" in candidates[1].title
    assert "Comp1" in candidates[2].title

def test_evaluation_extractor() -> None:
    repo = Mock(spec=EvaluationRepository)
    project_id = uuid4()
    source_id = uuid4()
    snapshot = EvaluationSnapshot.model_construct(
        metadata=ArtifactMetadata.model_construct(id=source_id),
        summary=EvaluationSummary.model_construct(synthesis="Synthesis"),
        findings=[
            EvaluationFinding.model_construct(
                category=FindingCategory.ARCHITECTURE,
                severity=FindingSeverity.BLOCKING,
                description="Blocker description",
                evidence="some evidence",
                recommendation="some recommendation",
            )
        ],
    )
    repo.get_by_project_id.return_value = Evaluation.model_construct(snapshots=[snapshot])
    extractor = EvaluationKnowledgeExtractor(repo)
    candidates = extractor.extract(project_id, source_id)
    assert len(candidates) == 2
    assert candidates[0].title == "Evaluation Synthesis"
    assert candidates[0].content == "Synthesis"
    assert "Blocking Finding" in candidates[1].title
    assert candidates[1].content == "Blocker description"

def test_extractor_registry() -> None:
    extractor = Mock()
    extractor.source_type = KnowledgeSourceType.RESEARCH_SNAPSHOT
    mock_candidate = Mock(spec=KnowledgeCandidate)
    extractor.extract.return_value = [mock_candidate]

    registry = ExtractorRegistry(extractor)
    res = registry.extract(uuid4(), KnowledgeSourceType.RESEARCH_SNAPSHOT, uuid4())
    assert res == [mock_candidate]
