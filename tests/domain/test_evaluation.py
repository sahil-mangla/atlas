from datetime import datetime
from uuid import UUID, uuid4

from engine.domain.enums import FindingSeverity, FindingCategory, FindingLifecycleStatus
from engine.domain.evaluation import (
    Evaluation,
    RequirementCoverage,
    EvaluationFinding,
    ReadinessDecision,
    EvaluationSummary,
    EvaluationSnapshot,
)
from engine.domain.metadata import ArtifactStatus, ArtifactMetadata


def test_evaluation_finding() -> None:
    finding = EvaluationFinding(
        severity=FindingSeverity.WARNING,
        category=FindingCategory.TRACEABILITY,
        description="Line is too long",
        evidence="Observed",
        recommendation="Shorten it",
        traceability_links=[uuid4()],
    )
    assert isinstance(finding.id, UUID)
    assert finding.description == "Line is too long"
    assert finding.severity == FindingSeverity.WARNING
    assert finding.category == FindingCategory.TRACEABILITY
    assert len(finding.traceability_links) == 1
    assert finding.lifecycle_status == FindingLifecycleStatus.ACTIVE


def test_requirement_coverage() -> None:
    coverage = RequirementCoverage(
        requirement_id=uuid4(),
        requirement_type="deliverable",
        description="Provide a robust API",
        status="satisfied",
        justification="All methods implemented",
    )
    assert isinstance(coverage.requirement_id, UUID)
    assert coverage.requirement_type == "deliverable"
    assert coverage.status == "satisfied"
    assert coverage.justification == "All methods implemented"


def test_readiness_decision() -> None:
    decision = ReadinessDecision(ready=True, justification="Everything looks solid")
    assert decision.ready is True
    assert decision.justification == "Everything looks solid"


def test_evaluation_defaults() -> None:
    project_id = uuid4()
    research_snapshot_id = uuid4()
    planning_snapshot_id = uuid4()
    architecture_snapshot_id = uuid4()

    evaluation = Evaluation(
        project_id=project_id,
        research_snapshot_id=research_snapshot_id,
        planning_snapshot_id=planning_snapshot_id,
        architecture_snapshot_id=architecture_snapshot_id,
    )
    assert isinstance(evaluation.id, UUID)
    assert evaluation.project_id == project_id
    assert evaluation.status == ArtifactStatus.DRAFT
    assert evaluation.research_snapshot_id == research_snapshot_id
    assert evaluation.planning_snapshot_id == planning_snapshot_id
    assert evaluation.architecture_snapshot_id == architecture_snapshot_id
    assert evaluation.findings == []
    assert evaluation.coverage == []
    assert evaluation.readiness_decision is None
    assert evaluation.summary is None
    assert evaluation.snapshots == []


def test_evaluation_snapshot() -> None:
    summary = EvaluationSummary(
        synthesis="Passes",
        total_findings=1,
        blocking_findings=0,
        satisfied_requirements=1,
    )
    decision = ReadinessDecision(ready=True, justification="Ready")
    snapshot = EvaluationSnapshot(
        metadata=ArtifactMetadata(version=1),
        research_snapshot_id=uuid4(),
        planning_snapshot_id=uuid4(),
        architecture_snapshot_id=uuid4(),
        findings=[],
        coverage=[],
        readiness_decision=decision,
        summary=summary,
    )
    assert snapshot.metadata.version == 1
    assert snapshot.readiness_decision.ready is True
    assert snapshot.summary.synthesis == "Passes"
