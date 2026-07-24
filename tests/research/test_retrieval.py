import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from engine.ai.context import IdentityContextStrategy
from engine.ai.executor import PromptExecutor
from engine.domain.project import Project
from engine.project.repository import ProjectRepository
from engine.research.retrieval import ResearchRetrievalService, _format_citation
from engine.research.sources.models import PaperCandidate
from tests.ai.test_adapters import MockAIProvider


class FakeProjectRepo(ProjectRepository):
    def __init__(self, project: Project | None) -> None:
        self._project = project

    def get_project_path(self, project_id: UUID) -> Path:  # pragma: no cover - unused
        raise NotImplementedError

    def save(self, project: Project) -> None:  # pragma: no cover - unused here
        pass

    def get_by_id(self, _project_id: UUID) -> Project | None:
        return self._project

    def discover(self) -> list[Project]:  # pragma: no cover - unused here
        return [self._project] if self._project else []


class FakeSource:
    name = "fake"
    last_call_failed = False

    def __init__(self, candidates: list[PaperCandidate]) -> None:
        self._candidates = candidates

    def search(self, _query: str, max_results: int) -> list[PaperCandidate]:
        return self._candidates[:max_results]


def _candidate(external_id: str, title: str = "Title") -> PaperCandidate:
    return PaperCandidate(
        title=title,
        authors=["A. Author"],
        year=2021,
        url=f"https://example.org/{external_id}",
        abstract="An abstract about the topic.",
        source="fake",
        external_id=external_id,
    )


def _executor_returning(payload: dict[str, Any]) -> PromptExecutor:
    provider = MockAIProvider(stubbed_response=json.dumps(payload))
    return PromptExecutor(provider, IdentityContextStrategy())


def test_retrieve_evidence_returns_empty_when_project_missing() -> None:
    service = ResearchRetrievalService(
        sources=[FakeSource([_candidate("1")])],
        project_repo=FakeProjectRepo(None),
        prompt_executor=_executor_returning({"summaries": ["x"]}),
    )
    assert service.retrieve_evidence(uuid4()) == []


def test_retrieve_evidence_returns_empty_when_no_candidates_found() -> None:
    project = Project(name="P", description="d", objective="o")
    service = ResearchRetrievalService(
        sources=[FakeSource([])],
        project_repo=FakeProjectRepo(project),
        prompt_executor=_executor_returning({"summaries": []}),
    )
    assert service.retrieve_evidence(project.id) == []


def test_retrieve_evidence_builds_grounded_evidence_from_candidates() -> None:
    project = Project(name="P", description="distributed consensus", objective="scale")
    candidate = _candidate("doi-1", title="Consensus at Scale")
    service = ResearchRetrievalService(
        sources=[FakeSource([candidate])],
        project_repo=FakeProjectRepo(project),
        prompt_executor=_executor_returning(
            {"summaries": ["The paper proposes a consensus protocol."]}
        ),
        max_candidates=5,
    )

    evidence = service.retrieve_evidence(project.id)

    assert len(evidence) == 1
    item = evidence[0]
    assert item.title == "Consensus at Scale"
    assert item.type == "paper"
    assert item.origin == "fake: https://example.org/doi-1"
    assert item.citation == _format_citation(candidate)
    assert item.summary == "The paper proposes a consensus protocol."


def test_retrieve_evidence_dedupes_across_sources_and_caps_at_max() -> None:
    project = Project(name="P", description="d", objective="o")
    dup = _candidate("same-id")
    service = ResearchRetrievalService(
        sources=[FakeSource([dup, _candidate("2")]), FakeSource([dup])],
        project_repo=FakeProjectRepo(project),
        prompt_executor=_executor_returning({"summaries": ["s1", "s2"]}),
        max_candidates=2,
    )

    evidence = service.retrieve_evidence(project.id)

    assert len(evidence) == 2
    assert {e.origin for e in evidence} == {
        "fake: https://example.org/same-id",
        "fake: https://example.org/2",
    }


def test_retrieve_evidence_falls_back_to_abstract_on_llm_failure() -> None:
    project = Project(name="P", description="d", objective="o")
    candidate = _candidate("1")
    provider = MockAIProvider(stubbed_response="not valid json")
    service = ResearchRetrievalService(
        sources=[FakeSource([candidate])],
        project_repo=FakeProjectRepo(project),
        prompt_executor=PromptExecutor(provider, IdentityContextStrategy()),
    )

    evidence = service.retrieve_evidence(project.id)

    assert len(evidence) == 1
    assert evidence[0].summary == candidate.abstract


def test_retrieve_evidence_falls_back_when_summary_count_mismatches() -> None:
    project = Project(name="P", description="d", objective="o")
    candidate = _candidate("1")
    service = ResearchRetrievalService(
        sources=[FakeSource([candidate])],
        project_repo=FakeProjectRepo(project),
        # Two summaries for one candidate -- a length mismatch.
        prompt_executor=_executor_returning({"summaries": ["a", "b"]}),
    )

    evidence = service.retrieve_evidence(project.id)

    assert len(evidence) == 1
    assert evidence[0].summary == candidate.abstract


def test_retrieve_evidence_gives_every_source_a_fair_share_when_capping() -> None:
    """A source whose results alone would fill the cap must not crowd out
    unique results from other sources -- they should be interleaved before
    the cap is applied, not concatenated source-by-source."""
    project = Project(name="P", description="d", objective="o")
    first_source_candidates = [_candidate(f"first-{i}") for i in range(5)]
    second_source_candidate = _candidate("second-unique")
    service = ResearchRetrievalService(
        sources=[
            FakeSource(first_source_candidates),
            FakeSource([second_source_candidate]),
        ],
        project_repo=FakeProjectRepo(project),
        prompt_executor=_executor_returning({"summaries": ["s1", "s2"]}),
        max_candidates=2,
    )

    evidence = service.retrieve_evidence(project.id)

    origins = {e.origin for e in evidence}
    assert "fake: https://example.org/second-unique" in origins


class RaisingSource:
    name = "raising"
    last_call_failed = False

    def search(self, _query: str, _max_results: int) -> list[PaperCandidate]:
        raise RuntimeError("unexpected bug in a source")


def test_retrieve_evidence_survives_a_source_raising_unexpectedly() -> None:
    """A bug in one source (violating the 'never raises' contract) must not
    take down retrieval for the other sources."""
    project = Project(name="P", description="d", objective="o")
    good_candidate = _candidate("1")
    service = ResearchRetrievalService(
        sources=[RaisingSource(), FakeSource([good_candidate])],
        project_repo=FakeProjectRepo(project),
        prompt_executor=_executor_returning({"summaries": ["s1"]}),
    )

    evidence = service.retrieve_evidence(project.id)

    assert len(evidence) == 1
    assert evidence[0].external_id == "1"


class FailingSource:
    name = "failing"
    last_call_failed = False

    def search(self, _query: str, _max_results: int) -> list[PaperCandidate]:
        self.last_call_failed = True
        return []


def test_retrieve_evidence_logs_outage_when_all_sources_fail(
    caplog: Any,
) -> None:
    project = Project(name="P", description="d", objective="o")
    service = ResearchRetrievalService(
        sources=[FailingSource(), FailingSource()],
        project_repo=FakeProjectRepo(project),
        prompt_executor=_executor_returning({"summaries": []}),
    )

    with caplog.at_level("ERROR", logger="engine.research.retrieval"):
        evidence = service.retrieve_evidence(project.id)

    assert evidence == []
    assert "outage" in caplog.text


def test_format_citation_handles_many_authors_and_missing_year() -> None:
    candidate = PaperCandidate(
        title="T",
        authors=["A", "B", "C", "D"],
        year=None,
        url="https://example.org/x",
        abstract="",
        source="fake",
        external_id="x",
    )
    citation = _format_citation(candidate)
    assert citation == "A, B, C et al.. T. https://example.org/x"
