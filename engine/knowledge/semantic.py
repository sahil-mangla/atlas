"""Semantic ranking of already-eligible published knowledge.

``KnowledgeRetrievalService`` keeps full ownership of *eligibility* (active
status, stage-profile categories, tags). This module only decides *order and
cut-off* among entries that already passed those filters, using embeddings.

``Embedder`` is a structural protocol defined here -- not imported from
``engine.ai`` -- so the knowledge subsystem keeps its "no AI imports" boundary
(ADR-003). Concrete embedders live in ``engine.ai`` and are injected by the
composition root.
"""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from engine.domain.knowledge import PublishedKnowledge
from engine.knowledge.vector_store import VectorRecord, VectorStore, VectorStoreError

_EMBED_BATCH_SIZE = 32


class Embedder(Protocol):
    """Turns text into vectors. Satisfied structurally by ``engine.ai`` adapters."""

    @property
    def model_id(self) -> str:
        """Stable identifier for the vector space (protocol + model)."""
        ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input text, in order."""
        ...


def entry_text(entry: PublishedKnowledge) -> str:
    """The text that represents an entry in embedding space."""
    tags = f"\nTags: {', '.join(entry.tags)}" if entry.tags else ""
    return f"{entry.title}\n\n{entry.content}{tags}"


class SemanticKnowledgeRanker:
    """Orders eligible entries by similarity to a query, indexing lazily.

    Entries are embedded the first time they are seen (or when the embedding
    model changes) and reused afterwards, so the index heals itself and needs
    no hooks on publish/supersede/deprecate. Deprecated or superseded entries
    can sit in the index harmlessly: callers only ever pass in entries that
    are currently eligible.
    """

    def __init__(self, embedder: Embedder, store: VectorStore) -> None:
        self._embedder = embedder
        self._store = store

    def rank(
        self,
        project_id: UUID,
        entries: Sequence[PublishedKnowledge],
        query_text: str,
        limit: int,
    ) -> list[PublishedKnowledge]:
        """Return up to ``limit`` of ``entries``, most relevant first.

        ``entries`` is expected in fallback (recency) order: if the index
        returns fewer hits than ``limit``, the remainder is filled from it in
        that order so the caller never receives less than it would without
        semantic ranking.

        Raises:
            VectorStoreError: The index is unusable.
            Exception: The embedder failed. Callers are expected to fall back.
        """
        if not entries or limit <= 0:
            return []
        if not query_text.strip():
            return list(entries[:limit])

        model_id = self._embedder.model_id
        self._index_missing(project_id, model_id, entries)

        query_vectors = self._embedder.embed([query_text])
        if len(query_vectors) != 1:
            raise VectorStoreError("Embedder returned no query vector.")
        hits = self._store.search(
            project_id,
            model_id,
            query_vectors[0],
            {entry.id for entry in entries},
            limit,
        )

        by_id = {entry.id: entry for entry in entries}
        ranked = [by_id[entry_id] for entry_id, _ in hits]
        seen = {entry.id for entry in ranked}
        ranked.extend(entry for entry in entries if entry.id not in seen)
        return ranked[:limit]

    def _index_missing(
        self,
        project_id: UUID,
        model_id: str,
        entries: Sequence[PublishedKnowledge],
    ) -> None:
        indexed = self._store.indexed(project_id, model_id)
        stale = [
            entry
            for entry in entries
            if indexed.get(entry.id) != entry.deduplication_fingerprint
        ]
        for start in range(0, len(stale), _EMBED_BATCH_SIZE):
            batch = stale[start : start + _EMBED_BATCH_SIZE]
            vectors = self._embedder.embed([entry_text(entry) for entry in batch])
            if len(vectors) != len(batch):
                raise VectorStoreError(
                    f"Embedder returned {len(vectors)} vectors for "
                    f"{len(batch)} entries."
                )
            self._store.upsert(
                project_id,
                model_id,
                [
                    VectorRecord(entry.id, entry.deduplication_fingerprint, vector)
                    for entry, vector in zip(batch, vectors, strict=True)
                ],
            )
