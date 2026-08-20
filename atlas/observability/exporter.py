"""Pluggable sinks for ``TraceRecord``s."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol, runtime_checkable

from atlas.observability.models import TraceRecord


@runtime_checkable
class TraceExporter(Protocol):
    """A sink that a finished ``TraceRecord`` is handed to."""

    def export(self, record: TraceRecord) -> None: ...


class NullExporter:
    """Discards every record -- the safe default for direct ``Atlas(...)``."""

    def export(self, record: TraceRecord) -> None:  # noqa: ARG002
        return None


class JsonlFileExporter:
    """Append-only, one-file-per-day JSONL trace sink.

    Deliberately NOT built on ``shared.atomic_write.atomic_write_text``: that
    helper rewrites the *entire* file via tempfile+``os.replace`` on every
    call, which fits the small whole-document JSON files every
    ``fs_repository.py`` writes but is wrong here -- a day's trace file grows
    unboundedly, so a whole-file rewrite per line would be O(n) per append
    (quadratic over a day) and would race any concurrent reader/writer of
    that day's file (two ``atlas`` invocations could plausibly append
    concurrently). A plain ``O_APPEND`` write is what append-only logs are
    for: a single ``write()`` to a file opened in append mode is atomic for
    writes under the platform's atomic-write limit (``PIPE_BUF``), comfortably
    true for one JSON line.
    """

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def export(self, record: TraceRecord) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / f"{record.timestamp.date().isoformat()}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
            f.flush()
            os.fsync(f.fileno())
