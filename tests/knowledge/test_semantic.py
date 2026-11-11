"""Semantic knowledge ranking: vector store, ranker, and retrieval fallback."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from engine.domain.enums import (
    KnowledgeActorType,
    KnowledgeCategory,
    KnowledgeSourceType,
    WorkflowStage,
)
from engine.domain.knowledge import (
    KnowledgeActor,
    KnowledgeProvenance,
    KnowledgeRetrievalQuery,
    PublishedKnowledge,
)
from engine.knowledge.semantic import SemanticKnowledgeRanker, entry_text
from engine.knowledge.services import KnowledgeRetrievalService
from engine.knowledge.vector_store import (
    SqliteVecStore,
    VectorRecord,
    VectorStoreError,
)

VOCAB = ("cache", "redis", "auth", "token", "queue", "kafka", "style", "format")
BASE_TIME = datetime(2026, 7, 1, tzinfo=UTC)


class BagOfWordsEmbedder:
    """Deterministic stand-in: one dimension per vocabulary word."""

    def __init__(self, model_id: str = "fake:v1") -> None:
        self.model_id = model_id
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        # The constant tail keeps vectors non-zero so cosine distance is defined.
        return [[float(t.lower().count(w)) for w in VOCAB] + [0.01] for t in texts]


class BrokenEmbedder:
    model_id = "fake:broken"

    def embed(self, _texts: Sequence[str]) -> list[list[float]]:
        raise RuntimeError("embedding backend down")


def _entry(
    project_id: UUID, title: str, content: str, age_days: int = 0
) -> PublishedKnowledge:
    actor = KnowledgeActor(actor_type=KnowledgeActorType.HUMAN, actor_id="u")
    return PublishedKnowledge(
        id=uuid4(),
        project_id=project_id,
        title=title,
        content=content,
        category=KnowledgeCategory.CONSTRAINT,
        tags=[],
        version=1,
        provenance=KnowledgeProvenance(
            source_type=KnowledgeSourceType.HUMAN_SUBMISSION,
            source_id=uuid4(),
            extracted_at=BASE_TIME,
            actor=actor,
        ),
        author=actor,
        published_at=BASE_TIME - timedelta(days=age_days),
        candidate_id=uuid4(),
        deduplication_fingerprint=f"fp-{title}",
    )


@pytest.fixture
def project_id() -> UUID:
    return uuid4()


@pytest.fixture
def store(tmp_path: Path) -> SqliteVecStore:
    project_repo = Mock()
    project_repo.get_project_path.return_value = tmp_path
    return SqliteVecStore(project_repo)


# --- SqliteVecStore -----------------------------------------------------------


def test_store_orders_by_cosine_distance_and_respects_allowed_ids(
    store: SqliteVecStore, project_id: UUID
) -> None:
    near, far, excluded = uuid4(), uuid4(), uuid4()
    store.upsert(
        project_id,
        "m",
        [
            VectorRecord(near, "a", [1.0, 0.1]),
            VectorRecord(far, "b", [0.0, 1.0]),
            VectorRecord(excluded, "c", [1.0, 0.0]),  # closest, but not eligible
        ],
    )

    hits = store.search(project_id, "m", [1.0, 0.0], {near, far}, limit=5)

    assert [entry_id for entry_id, _ in hits] == [near, far]
    assert hits[0][1] < hits[1][1]
    assert store.search(project_id, "m", [1.0, 0.0], {near, far}, limit=1) == hits[:1]


def test_store_isolates_models_and_reports_fingerprints(
    store: SqliteVecStore, project_id: UUID
) -> None:
    entry_id = uuid4()
    store.upsert(project_id, "m1", [VectorRecord(entry_id, "fp1", [1.0, 0.0])])

    assert store.indexed(project_id, "m1") == {entry_id: "fp1"}
    assert store.indexed(project_id, "m2") == {}
    assert store.search(project_id, "m2", [1.0, 0.0], {entry_id}, limit=5) == []


def test_store_delete_all_drops_the_index(
    store: SqliteVecStore, project_id: UUID
) -> None:
    entry_id = uuid4()
    store.upsert(project_id, "m", [VectorRecord(entry_id, "fp", [1.0, 0.0])])

    store.delete_all(project_id)

    assert store.indexed(project_id, "m") == {}


def test_store_dimension_mismatch_raises_store_error(
    store: SqliteVecStore, project_id: UUID
) -> None:
    entry_id = uuid4()
    store.upsert(project_id, "m", [VectorRecord(entry_id, "fp", [1.0, 0.0])])

    with pytest.raises(VectorStoreError):
        store.search(project_id, "m", [1.0, 0.0, 0.0], {entry_id}, limit=5)


# --- SemanticKnowledgeRanker --------------------------------------------------


def test_ranker_orders_by_relevance_not_recency(
    store: SqliteVecStore, project_id: UUID
) -> None:
    newest_irrelevant = _entry(project_id, "Code style", "format style rules", 0)
    older_relevant = _entry(project_id, "Redis cache", "cache redis eviction", 5)
    ranker = SemanticKnowledgeRanker(BagOfWordsEmbedder(), store)

    ranked = ranker.rank(
        project_id, [newest_irrelevant, older_relevant], "redis cache sizing", limit=1
    )

    assert ranked == [older_relevant]


def test_ranker_embeds_each_entry_once_and_reembeds_on_model_change(
    store: SqliteVecStore, project_id: UUID
) -> None:
    entries = [
        _entry(project_id, "Redis cache", "cache redis", 0),
        _entry(project_id, "Auth token", "auth token", 1),
    ]
    embedder = BagOfWordsEmbedder("fake:v1")
    ranker = SemanticKnowledgeRanker(embedder, store)

    ranker.rank(project_id, entries, "cache", limit=2)
    ranker.rank(project_id, entries, "token", limit=2)

    # First call: 2 entries + query. Second call: query only (entries cached).
    assert [len(call) for call in embedder.calls] == [2, 1, 1]

    new_model = BagOfWordsEmbedder("fake:v2")
    SemanticKnowledgeRanker(new_model, store).rank(
        project_id, entries, "cache", limit=2
    )
    assert [len(call) for call in new_model.calls] == [2, 1]


def test_ranker_only_considers_the_entries_it_is_given(
    store: SqliteVecStore, project_id: UUID
) -> None:
    """A previously indexed entry that is no longer eligible must not return."""
    gone = _entry(project_id, "Redis cache", "cache redis cache redis", 0)
    kept = _entry(project_id, "Auth token", "auth token", 1)
    ranker = SemanticKnowledgeRanker(BagOfWordsEmbedder(), store)
    ranker.rank(project_id, [gone, kept], "redis cache", limit=2)  # indexes both

    ranked = ranker.rank(project_id, [kept], "redis cache", limit=5)

    assert ranked == [kept]


def test_ranker_blank_query_keeps_input_order(
    store: SqliteVecStore, project_id: UUID
) -> None:
    entries = [_entry(project_id, f"t{i}", "x", i) for i in range(3)]
    embedder = BagOfWordsEmbedder()

    ranked = SemanticKnowledgeRanker(embedder, store).rank(
        project_id, entries, "   ", limit=2
    )

    assert ranked == entries[:2]
    assert embedder.calls == []


def test_entry_text_includes_title_content_and_tags(project_id: UUID) -> None:
    entry = _entry(project_id, "Title", "Body")
    tagged = entry.model_copy(update={"tags": ["a", "b"]})

    assert entry_text(entry) == "Title\n\nBody"
    assert entry_text(tagged).endswith("Tags: a, b")


# --- KnowledgeRetrievalService integration -----------------------------------


def _service(
    entries: list[PublishedKnowledge],
    ranker: SemanticKnowledgeRanker | None,
    project: object | None = None,
) -> KnowledgeRetrievalService:
    repo = Mock()
    repo.list_published.return_value = entries
    project_repo = Mock()
    project_repo.get_by_id.return_value = project
    return KnowledgeRetrievalService(repo, ranker, project_repo)


def test_retrieval_uses_semantic_order_when_ranker_configured(
    store: SqliteVecStore, project_id: UUID
) -> None:
    newest = _entry(project_id, "Code style", "format style rules", 0)
    relevant = _entry(project_id, "Redis cache", "cache redis eviction", 9)
    service = _service(
        [newest, relevant], SemanticKnowledgeRanker(BagOfWordsEmbedder(), store)
    )

    context = service.retrieve(
        _query(project_id, query_text="size the redis cache", max_entries=1)
    )

    assert context.entry_ids == [relevant.id]


def test_retrieval_derives_query_from_project_objective(
    store: SqliteVecStore, project_id: UUID
) -> None:
    newest = _entry(project_id, "Code style", "format style rules", 0)
    relevant = _entry(project_id, "Kafka queue", "kafka queue ordering", 9)
    project = SimpleNamespace(objective="Build a kafka queue", description="")
    service = _service(
        [newest, relevant],
        SemanticKnowledgeRanker(BagOfWordsEmbedder(), store),
        project,
    )

    context = service.retrieve(_query(project_id, max_entries=1))

    assert context.entry_ids == [relevant.id]


def test_retrieval_falls_back_to_recency_when_ranker_fails(
    project_id: UUID,
) -> None:
    newest = _entry(project_id, "Code style", "format style rules", 0)
    older = _entry(project_id, "Redis cache", "cache redis", 9)
    broken = SemanticKnowledgeRanker(BrokenEmbedder(), Mock())
    service = _service([older, newest], broken)

    context = service.retrieve(_query(project_id, query_text="redis", max_entries=1))

    assert context.entry_ids == [newest.id]


def test_retrieval_skips_ranker_for_a_single_entry(project_id: UUID) -> None:
    only = _entry(project_id, "Redis cache", "cache redis", 0)
    ranker = Mock()
    service = _service([only], ranker)

    context = service.retrieve(_query(project_id, query_text="redis"))

    assert context.entry_ids == [only.id]
    ranker.rank.assert_not_called()


def test_retrieval_without_ranker_is_unchanged(project_id: UUID) -> None:
    newest = _entry(project_id, "A", "x", 0)
    older = _entry(project_id, "B", "y", 5)
    service = _service([older, newest], None)

    context = service.retrieve(_query(project_id, query_text="anything"))

    assert context.entry_ids == [newest.id, older.id]


def _query(
    project_id: UUID, query_text: str = "", max_entries: int = 20
) -> KnowledgeRetrievalQuery:
    return KnowledgeRetrievalQuery(
        project_id=project_id,
        stage=WorkflowStage.RESEARCH,
        categories=[KnowledgeCategory.CONSTRAINT],
        query_text=query_text,
        max_entries=max_entries,
    )
