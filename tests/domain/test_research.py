from uuid import UUID, uuid4

from engine.domain.enums import ResearchStatus
from engine.domain.research import (
    Assumption,
    Constraint,
    Evidence,
    Opportunity,
    ProblemDefinition,
    Research,
    ResearchFinding,
    ResearchSnapshot,
    ResearchSource,
    ResearchSummary,
)


def test_research_models() -> None:
    problem = ProblemDefinition(statement="Scale DB", objectives=["Find good DB"])
    assert problem.statement == "Scale DB"

    source = ResearchSource(title="Postgres Docs", url_or_reference="https://pg.org")
    assert isinstance(source.id, UUID)
    assert source.title == "Postgres Docs"

    evidence = Evidence(
        type="literature",
        title="Postgres scales",
        origin="Docs",
        citation="PG v15",
        summary="Works well",
    )
    assert isinstance(evidence.id, UUID)
    assert evidence.type == "literature"

    finding = ResearchFinding(
        title="PG is good", summary="Use PG", evidence_ids=[evidence.id]
    )
    assert isinstance(finding.id, UUID)
    assert finding.evidence_ids == [evidence.id]

    constraint = Constraint(
        description="Must use SQL", impact="Limits NoSQL", finding_ids=[finding.id]
    )
    assert isinstance(constraint.id, UUID)
    assert constraint.finding_ids == [finding.id]

    assumption = Assumption(description="Load < 10k", risk="Might break")
    assert isinstance(assumption.id, UUID)

    opportunity = Opportunity(
        title="Use JSONB", description="Store JSON", finding_ids=[finding.id]
    )
    assert isinstance(opportunity.id, UUID)
    assert opportunity.finding_ids == [finding.id]


def test_research_aggregate() -> None:
    project_id = uuid4()
    research = Research(project_id=project_id)
    assert isinstance(research.id, UUID)
    assert research.project_id == project_id
    assert research.status == ResearchStatus.DRAFT
    assert research.snapshots == []

    # Active state
    assert research.problem_definition is None
    assert research.sources == []
    assert research.evidence == []


def test_research_snapshot() -> None:
    summary = ResearchSummary(synthesis="PG wins", key_takeaways=["Use PG"])
    problem = ProblemDefinition(statement="Scale DB", objectives=[])

    snapshot = ResearchSnapshot(
        version=1,
        problem_definition=problem,
        research_sources=[],
        evidence=[],
        findings=[],
        constraints=[],
        assumptions=[],
        opportunities=[],
        open_questions=[],
        summary=summary,
        confidence=0.9,
    )
    assert snapshot.version == 1
    assert snapshot.confidence == 0.9
