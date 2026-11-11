"""Embedded vector index for published engineering knowledge.

The index is a *derived cache*: ``.atlas/knowledge.json`` stays the single
source of truth for what knowledge exists, whether it is active, and what it
says. Nothing here can publish, change, or resurrect an entry -- it only
answers "which of these already-eligible entries is closest to this query?".
Because of that, the index file can always be deleted and rebuilt, and every
caller treats a ``VectorStoreError`` as "fall back to the non-semantic path".

Per-project knowledge corpora are small (human-reviewed entries), so search is
an exact scan with sqlite-vec's cosine distance rather than an approximate
index. That keeps results deterministic, needs no fixed embedding dimension,
and lets a model change simply re-embed.
"""

import sqlite3
from abc import ABC, abstractmethod
from collections.abc import Collection, Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import sqlite_vec

from engine.project.repository import ProjectRepository


class VectorStoreError(Exception):
    """The vector index is unavailable or could not complete an operation."""


@dataclass(frozen=True)
class VectorRecord:
    """One embedded knowledge entry.

    ``fingerprint`` is the entry's ``deduplication_fingerprint``. Published
    content is immutable, so a matching fingerprint means the stored vector is
    still valid and the entry never needs re-embedding.
    """

    entry_id: UUID
    fingerprint: str
    vector: Sequence[float]


class VectorStore(ABC):
    """Project-scoped nearest-neighbour index over knowledge entry vectors."""

    @abstractmethod
    def indexed(self, project_id: UUID, model_id: str) -> dict[UUID, str]:
        """Return ``{entry_id: fingerprint}`` for vectors made by ``model_id``."""

    @abstractmethod
    def upsert(
        self, project_id: UUID, model_id: str, records: Sequence[VectorRecord]
    ) -> None:
        """Insert or replace vectors for ``records`` under ``model_id``."""

    @abstractmethod
    def search(
        self,
        project_id: UUID,
        model_id: str,
        vector: Sequence[float],
        entry_ids: Collection[UUID],
        limit: int,
    ) -> list[tuple[UUID, float]]:
        """Return up to ``limit`` ``(entry_id, distance)`` pairs, nearest first.

        Only ids in ``entry_ids`` are considered, so the caller's own
        eligibility filtering (status, category, tags) is never bypassed.
        """

    @abstractmethod
    def delete_all(self, project_id: UUID) -> None:
        """Drop the project's index entirely."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_vectors (
    entry_id    TEXT PRIMARY KEY,
    model_id    TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    embedding   BLOB NOT NULL
)
"""


class SqliteVecStore(VectorStore):
    """sqlite-vec backed store at ``<project>/.atlas/knowledge.vec.db``."""

    def __init__(self, project_repo: ProjectRepository) -> None:
        self._project_repo = project_repo

    def _path(self, project_id: UUID) -> Path:
        return (
            self._project_repo.get_project_path(project_id)
            / ".atlas"
            / "knowledge.vec.db"
        )

    def _connect(self, project_id: UUID) -> sqlite3.Connection:
        path = self._path(project_id)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(path)
        except (OSError, sqlite3.Error) as exc:
            raise VectorStoreError(
                f"Cannot open vector index at {path}: {exc}"
            ) from exc
        try:
            connection.enable_load_extension(True)
            sqlite_vec.load(connection)
            connection.enable_load_extension(False)
            connection.execute(_SCHEMA)
        except (AttributeError, sqlite3.Error) as exc:
            connection.close()
            # AttributeError: this Python's sqlite3 was built without
            # extension loading (some system/macOS builds).
            raise VectorStoreError(
                f"sqlite-vec is unavailable for the vector index at {path}: {exc}"
            ) from exc
        return connection

    def indexed(self, project_id: UUID, model_id: str) -> dict[UUID, str]:
        try:
            with closing(self._connect(project_id)) as connection:
                rows = connection.execute(
                    "SELECT entry_id, fingerprint FROM knowledge_vectors "
                    "WHERE model_id = ?",
                    (model_id,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise VectorStoreError(f"Vector index read failed: {exc}") from exc
        return {UUID(entry_id): fingerprint for entry_id, fingerprint in rows}

    def upsert(
        self, project_id: UUID, model_id: str, records: Sequence[VectorRecord]
    ) -> None:
        if not records:
            return
        rows = [
            (
                str(record.entry_id),
                model_id,
                record.fingerprint,
                sqlite_vec.serialize_float32(list(record.vector)),
            )
            for record in records
        ]
        try:
            with closing(self._connect(project_id)) as connection, connection:
                connection.executemany(
                    "INSERT OR REPLACE INTO knowledge_vectors "
                    "(entry_id, model_id, fingerprint, embedding) "
                    "VALUES (?, ?, ?, ?)",
                    rows,
                )
        except sqlite3.Error as exc:
            raise VectorStoreError(f"Vector index write failed: {exc}") from exc

    def search(
        self,
        project_id: UUID,
        model_id: str,
        vector: Sequence[float],
        entry_ids: Collection[UUID],
        limit: int,
    ) -> list[tuple[UUID, float]]:
        if limit <= 0 or not entry_ids:
            return []
        allowed = set(entry_ids)
        try:
            with closing(self._connect(project_id)) as connection:
                rows = connection.execute(
                    "SELECT entry_id, vec_distance_cosine(embedding, ?) AS distance "
                    "FROM knowledge_vectors WHERE model_id = ? "
                    "ORDER BY distance, entry_id",
                    (sqlite_vec.serialize_float32(list(vector)), model_id),
                ).fetchall()
        except sqlite3.Error as exc:
            # Includes a dimension mismatch between the query and stored vectors.
            raise VectorStoreError(f"Vector index search failed: {exc}") from exc
        hits = [
            (UUID(entry_id), float(distance))
            for entry_id, distance in rows
            if UUID(entry_id) in allowed
        ]
        return hits[:limit]

    def delete_all(self, project_id: UUID) -> None:
        path = self._path(project_id)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise VectorStoreError(
                f"Cannot delete vector index at {path}: {exc}"
            ) from exc
