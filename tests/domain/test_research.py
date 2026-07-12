from uuid import UUID, uuid4

from engine.domain.enums import ResearchStatus
from engine.domain.research import (
    KnowledgeGap,
    Research,
    ResearchFinding,
    ResearchTopic,
)


def test_research_sub_models() -> None:
    topic = ResearchTopic(title="DB Scaling", description="Evaluate postgres vs mongo")
    assert isinstance(topic.id, UUID)
    assert topic.title == "DB Scaling"

    finding = ResearchFinding(
        title="Postgres works",
        summary="Postgres scales well enough for current load",
        source="https://example.com/postgres-scaling",
    )
    assert isinstance(finding.id, UUID)
    assert finding.title == "Postgres works"
    assert finding.source == "https://example.com/postgres-scaling"

    gap = KnowledgeGap(
        description="Missing load test data",
        impact="Could fail under peak load",
    )
    assert isinstance(gap.id, UUID)
    assert gap.description == "Missing load test data"


def test_research_defaults() -> None:
    project_id = uuid4()
    research = Research(project_id=project_id)

    assert isinstance(research.id, UUID)
    assert research.project_id == project_id
    assert research.problem_statement == ""
    assert research.status == ResearchStatus.PLANNED
    assert research.topics == []
    assert research.literature == []
    assert research.findings == []
    assert research.references == []
    assert research.knowledge_gaps == []


def test_research_custom() -> None:
    research_id = uuid4()
    project_id = uuid4()
    topic = ResearchTopic(title="DB Scaling")
    finding = ResearchFinding(title="Postgres works", summary="Postgres works well")
    gap = KnowledgeGap(description="Missing load test data")

    research = Research(
        id=research_id,
        project_id=project_id,
        problem_statement="Investigate data persistence options",
        status=ResearchStatus.IN_PROGRESS,
        topics=[topic],
        literature=["Ref paper 1"],
        findings=[finding],
        references=["https://google.com"],
        knowledge_gaps=[gap],
    )

    assert research.id == research_id
    assert research.project_id == project_id
    assert research.problem_statement == "Investigate data persistence options"
    assert research.status == ResearchStatus.IN_PROGRESS
    assert len(research.topics) == 1
    assert research.topics[0].title == "DB Scaling"
    assert research.literature == ["Ref paper 1"]
    assert len(research.findings) == 1
    assert research.findings[0].title == "Postgres works"
    assert research.references == ["https://google.com"]
    assert len(research.knowledge_gaps) == 1
    assert research.knowledge_gaps[0].description == "Missing load test data"
