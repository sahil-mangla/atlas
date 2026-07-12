from datetime import datetime
from uuid import UUID, uuid4

from engine.domain.enums import EvaluationStatus, FindingSeverity
from engine.domain.evaluation import (
    Evaluation,
    RequirementCoverage,
    ReviewFinding,
)


def test_review_finding() -> None:
    finding = ReviewFinding(
        description="Line is too long",
        severity=FindingSeverity.WARNING,
        location="engine/domain/project.py:L10",
    )
    assert isinstance(finding.id, UUID)
    assert finding.description == "Line is too long"
    assert finding.severity == FindingSeverity.WARNING
    assert finding.location == "engine/domain/project.py:L10"


def test_requirement_coverage() -> None:
    coverage = RequirementCoverage(
        requirement_id="REQ-01",
        description="Provide a robust API",
        covered=True,
        notes="All methods implemented",
    )
    assert coverage.requirement_id == "REQ-01"
    assert coverage.description == "Provide a robust API"
    assert coverage.covered is True
    assert coverage.notes == "All methods implemented"


def test_evaluation_defaults() -> None:
    project_id = uuid4()
    evaluation = Evaluation(project_id=project_id)
    assert isinstance(evaluation.id, UUID)
    assert evaluation.project_id == project_id
    assert evaluation.specification_id is None
    assert evaluation.status == EvaluationStatus.PENDING
    assert evaluation.quality_summary == ""
    assert evaluation.requirement_coverage == []
    assert evaluation.findings == []
    assert evaluation.recommendations == []
    assert evaluation.evaluated_at is None


def test_evaluation_custom() -> None:
    eval_id = uuid4()
    project_id = uuid4()
    spec_id = uuid4()
    finding = ReviewFinding(description="Warning", severity=FindingSeverity.WARNING)
    coverage = RequirementCoverage(requirement_id="REQ-02", description="Robust API")

    now = datetime.now()
    evaluation = Evaluation(
        id=eval_id,
        project_id=project_id,
        specification_id=spec_id,
        status=EvaluationStatus.FAILED,
        quality_summary="Coverage 80%",
        requirement_coverage=[coverage],
        findings=[finding],
        recommendations=["Add more tests"],
        evaluated_at=now,
    )

    assert evaluation.id == eval_id
    assert evaluation.project_id == project_id
    assert evaluation.specification_id == spec_id
    assert evaluation.status == EvaluationStatus.FAILED
    assert evaluation.quality_summary == "Coverage 80%"
    assert len(evaluation.requirement_coverage) == 1
    assert evaluation.requirement_coverage[0].requirement_id == "REQ-02"
    assert len(evaluation.findings) == 1
    assert evaluation.findings[0].description == "Warning"
    assert evaluation.recommendations == ["Add more tests"]
    assert evaluation.evaluated_at == now
