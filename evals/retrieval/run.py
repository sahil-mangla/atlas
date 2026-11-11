"""Measure knowledge-retrieval quality and latency.

Compares, over the labelled queries in ``queries.yaml`` and the corpus from
``corpus.py``:

* ``recency``  -- Atlas's retrieval BEFORE semantic ranking: the real
  ``KnowledgeRetrievalService`` with no ranker (newest-first, query-blind).
* ``bm25``     -- a plain keyword baseline (Okapi BM25), for reference.
* ``vector``   -- the real service with ``SemanticKnowledgeRanker`` +
  ``SqliteVecStore`` + a real embedding model (Ollama by default).

Run:  uv run python -m evals.retrieval --model nomic-embed-text [--cold]
"""

import argparse
import json
import math
import platform
import random
import re
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from uuid import UUID

import yaml

from engine.ai.config import ProviderConfig
from engine.ai.embedding_factory import EmbeddingFactory
from engine.domain.enums import KnowledgeCategory, WorkflowStage
from engine.domain.knowledge import KnowledgeRetrievalQuery, PublishedKnowledge
from engine.knowledge.semantic import SemanticKnowledgeRanker, entry_text
from engine.knowledge.services import KnowledgeRetrievalService
from engine.knowledge.vector_store import SqliteVecStore
from engine.research.retrieval import _STOPWORDS
from evals.retrieval.corpus import PROJECT_ID, build_corpus, entry_id_for

QUERIES_PATH = Path(__file__).with_name("queries.yaml")
RESULTS_PATH = Path(__file__).with_name("results.json")
KS = (1, 3, 5, 10, 20)  # 20 == the pipeline's real cap (stage profile max_entries)
LATENCY_REPS = 5
INDEX_REPS = 3
BOOTSTRAP_RESAMPLES = 2000
_TOKEN = re.compile(r"[a-z0-9]+")
_NEAREST_RANK_P50, _NEAREST_RANK_P95 = 0.50, 0.95


def out(line: str = "") -> None:
    sys.stdout.write(line + "\n")


class TimedEmbedder:
    """Wraps an embedder to record how long each ``embed`` call took."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.calls: list[tuple[int, float]] = []

    @property
    def model_id(self) -> str:
        return str(self._inner.model_id)

    def embed(self, texts: Any) -> list[list[float]]:
        started = time.perf_counter()
        vectors: list[list[float]] = self._inner.embed(texts)
        self.calls.append((len(texts), time.perf_counter() - started))
        return vectors


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS]


class Bm25:
    """Okapi BM25 over entry_text(); k1=1.5, b=0.75."""

    def __init__(self, entries: list[PublishedKnowledge]) -> None:
        self._ids = [e.id for e in entries]
        self._docs = [Counter(tokenize(entry_text(e))) for e in entries]
        self._lengths = [sum(d.values()) for d in self._docs]
        self._avg = sum(self._lengths) / len(self._lengths)
        n = len(self._docs)
        df: Counter[str] = Counter()
        for doc in self._docs:
            df.update(doc.keys())
        self._idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def rank(self, query: str, limit: int) -> list[UUID]:
        terms = tokenize(query)
        scores: list[tuple[float, str, UUID]] = []
        for entry_id, doc, length in zip(
            self._ids, self._docs, self._lengths, strict=True
        ):
            score = 0.0
            for term in terms:
                freq = doc.get(term, 0)
                if freq:
                    norm = 1.5 * (1 - 0.75 + 0.75 * length / self._avg)
                    score += self._idf[term] * freq * 2.5 / (freq + norm)
            scores.append((-score, str(entry_id), entry_id))
        scores.sort()
        return [entry_id for _, _, entry_id in scores[:limit]]


def metrics_for(ranked: list[UUID], relevant: set[UUID]) -> dict[str, float]:
    result: dict[str, float] = {}
    for k in KS:
        found = len(set(ranked[:k]) & relevant)
        result[f"hit@{k}"] = 1.0 if found else 0.0
        result[f"recall@{k}"] = found / len(relevant)
    first = next((i for i, e in enumerate(ranked[: max(KS)], 1) if e in relevant), 0)
    result["mrr@20"] = 1.0 / first if first else 0.0
    return result


def bootstrap_ci(values: list[float], seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    means = sorted(
        statistics.fmean(rng.choices(values, k=len(values)))
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    return means[int(0.025 * BOOTSTRAP_RESAMPLES)], means[
        int(0.975 * BOOTSTRAP_RESAMPLES)
    ]


def nearest_rank(sorted_values: list[float], p: float) -> float:
    return sorted_values[max(0, math.ceil(p * len(sorted_values)) - 1)]


def make_service(
    entries: list[PublishedKnowledge], ranker: SemanticKnowledgeRanker | None
) -> KnowledgeRetrievalService:
    repo = Mock()
    repo.list_published.return_value = entries
    return KnowledgeRetrievalService(repo, ranker, None)


def retrieve_ids(
    service: KnowledgeRetrievalService, query_text: str, limit: int = max(KS)
) -> list[UUID]:
    query = KnowledgeRetrievalQuery(
        project_id=PROJECT_ID,
        stage=WorkflowStage.ARCHITECTURE,  # profile includes DECISION_SUMMARY
        categories=[KnowledgeCategory.DECISION_SUMMARY],
        query_text=query_text,
        max_entries=limit,
    )
    return service.retrieve(query).entry_ids


def new_store(tmp: Path) -> SqliteVecStore:
    project_repo = Mock()
    project_repo.get_project_path.return_value = tmp
    return SqliteVecStore(project_repo)


def main() -> None:  # noqa: PLR0915
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", default="OLLAMA")
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument(
        "--cold", action="store_true", help="unload the Ollama model first"
    )
    args = parser.parse_args()

    entries, section_ids = build_corpus()
    queries = yaml.safe_load(QUERIES_PATH.read_text(encoding="utf-8"))
    by_section = {sid: uid for uid, sid in section_ids.items()}
    relevant = {q["id"]: {entry_id_for(r) for r in q["relevant"]} for q in queries}
    for q in queries:
        assert all(entry_id_for(r) in section_ids for r in q["relevant"]), q["id"]
    assert by_section

    config = ProviderConfig(
        protocol=args.protocol, endpoint=args.endpoint, model=args.model
    )
    embedder = TimedEmbedder(EmbeddingFactory().resolve(config))
    report: dict[str, Any] = {
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": platform.python_version(),
            "ollama": subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip(),
        },
        "embedder": embedder.model_id,
        "corpus": {
            "entries": len(entries),
            "chars_total": sum(len(entry_text(e)) for e in entries),
            "chars_max_entry": max(len(entry_text(e)) for e in entries),
            "chars_mean_entry": round(
                statistics.fmean(len(entry_text(e)) for e in entries), 1
            ),
        },
        "queries": len(queries),
        "labels": sum(len(q["relevant"]) for q in queries),
    }

    # --- cold first call -----------------------------------------------------
    if args.cold:
        subprocess.run(
            ["ollama", "stop", args.model],
            capture_output=True,
            check=False,
        )
        time.sleep(2)
    started = time.perf_counter()
    first_vector = embedder.embed(["warm-up"])[0]
    report["first_embed_call_s"] = round(time.perf_counter() - started, 4)
    report["first_embed_call_was_cold"] = args.cold
    report["embedding_dimensions"] = len(first_vector)

    # --- indexing time (fresh DB each rep; model already loaded) --------------
    index_seconds: list[float] = []
    for _ in range(INDEX_REPS):
        with tempfile.TemporaryDirectory() as tmp:
            ranker = SemanticKnowledgeRanker(embedder, new_store(Path(tmp)))
            started = time.perf_counter()
            ranker._index_missing(PROJECT_ID, embedder.model_id, entries)
            index_seconds.append(time.perf_counter() - started)
    report["indexing_s"] = [round(s, 3) for s in index_seconds]

    # --- quality + latency on one persistent index --------------------------
    with tempfile.TemporaryDirectory() as tmp:
        store = new_store(Path(tmp))
        ranker = SemanticKnowledgeRanker(embedder, store)
        ranker._index_missing(PROJECT_ID, embedder.model_id, entries)
        report["index_file_bytes"] = (
            (Path(tmp) / ".atlas" / "knowledge.vec.db").stat().st_size
        )

        systems: dict[str, KnowledgeRetrievalService | Bm25] = {
            "recency": make_service(entries, None),
            "bm25": Bm25(entries),
            "vector": make_service(entries, ranker),
        }
        per_query: dict[str, dict[str, dict[str, float]]] = {n: {} for n in systems}
        for q in queries:
            for name, system in systems.items():
                ranked = (
                    system.rank(q["query"], max(KS))
                    if isinstance(system, Bm25)
                    else retrieve_ids(system, q["query"])
                )
                per_query[name][q["id"]] = metrics_for(ranked, relevant[q["id"]])

        summary: dict[str, dict[str, Any]] = {}
        for name, rows in per_query.items():
            summary[name] = {}
            for metric in rows[queries[0]["id"]]:
                values = [row[metric] for row in rows.values()]
                lo, hi = bootstrap_ci(values)
                summary[name][metric] = {
                    "mean": round(statistics.fmean(values), 4),
                    "ci95": [round(lo, 4), round(hi, 4)],
                }
        report["quality"] = summary
        # Paired comparison: bootstrap the per-query difference (vector - other),
        # which is far tighter than comparing two unpaired intervals.
        report["paired_vector_minus"] = {
            other: {
                metric: {
                    "mean_diff": round(
                        statistics.fmean(
                            per_query["vector"][q["id"]][metric]
                            - per_query[other][q["id"]][metric]
                            for q in queries
                        ),
                        4,
                    ),
                    "ci95": [
                        round(x, 4)
                        for x in bootstrap_ci(
                            [
                                per_query["vector"][q["id"]][metric]
                                - per_query[other][q["id"]][metric]
                                for q in queries
                            ]
                        )
                    ],
                    "vector_better_queries": sum(
                        per_query["vector"][q["id"]][metric]
                        > per_query[other][q["id"]][metric]
                        for q in queries
                    ),
                    "other_better_queries": sum(
                        per_query["vector"][q["id"]][metric]
                        < per_query[other][q["id"]][metric]
                        for q in queries
                    ),
                }
                for metric in ("hit@1", "hit@5", "recall@5", "mrr@20")
            }
            for other in ("bm25", "recency")
        }
        # Expected recall@k of a uniformly random ranking is exactly k / corpus size.
        report["random_expected_recall_at_k"] = {
            str(k): round(k / len(entries), 4) for k in KS
        }
        report["per_query_mrr"] = {
            n: {qid: round(m["mrr@20"], 3) for qid, m in rows.items()}
            for n, rows in per_query.items()
        }

        # --- query latency (warm, steady state) -------------------------------
        service = systems["vector"]
        assert isinstance(service, KnowledgeRetrievalService)
        samples: list[float] = []
        embed_samples: list[float] = []
        for _ in range(LATENCY_REPS):
            for q in queries:
                before = len(embedder.calls)
                started = time.perf_counter()
                retrieve_ids(service, q["query"])
                samples.append(time.perf_counter() - started)
                embed_samples.append(sum(d for _, d in embedder.calls[before:]))
        ordered = sorted(samples)
        embed_ordered = sorted(embed_samples)
        report["query_latency_ms"] = {
            "samples": len(samples),
            "distinct_queries": len(queries),
            "p50": round(nearest_rank(ordered, _NEAREST_RANK_P50) * 1000, 2),
            "p95": round(nearest_rank(ordered, _NEAREST_RANK_P95) * 1000, 2),
            "min": round(ordered[0] * 1000, 2),
            "max": round(ordered[-1] * 1000, 2),
            "embed_call_p50": round(
                nearest_rank(embed_ordered, _NEAREST_RANK_P50) * 1000, 2
            ),
            "embed_call_p95": round(
                nearest_rank(embed_ordered, _NEAREST_RANK_P95) * 1000, 2
            ),
        }
        bm25 = systems["bm25"]
        assert isinstance(bm25, Bm25)
        bm25_samples = []
        for q in queries:
            started = time.perf_counter()
            bm25.rank(q["query"], max(KS))
            bm25_samples.append(time.perf_counter() - started)
        report["bm25_latency_ms_p50"] = round(
            nearest_rank(sorted(bm25_samples), _NEAREST_RANK_P50) * 1000, 3
        )

    RESULTS_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    out(json.dumps({k: v for k, v in report.items() if k != "per_query_mrr"}, indent=2))
    out(f"\nwrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
