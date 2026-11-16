"""Builds a real, fully-wired Atlas platform for an eval run.

Reuses ``atlas.testing.create_test_platform`` rather than duplicating its
production-shaped service wiring: it supports everything an eval run needs
(real repositories/services, an injectable AIProvider, an injectable
workspace root, an injectable TraceExporter).
"""

from __future__ import annotations

from pathlib import Path

from atlas_eng import Atlas
from atlas_eng.engine.ai.provider import AIProvider
from atlas_eng.observability.exporter import TraceExporter
from atlas_eng.observability.models import TraceRecord
from atlas_eng.testing import create_test_platform


class RecordingExporter:
    """Captures every TraceRecord in-memory, in order, for the runner to score."""

    def __init__(self) -> None:
        self.records: list[TraceRecord] = []

    def export(self, record: TraceRecord) -> None:
        self.records.append(record)


def build_eval_platform(
    run_dir: Path, ai_provider: AIProvider
) -> tuple[Atlas, RecordingExporter]:
    """Construct an Atlas instance wired to `ai_provider`, with instrumentation
    forced on so every request produces a scorable TraceRecord.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    exporter: TraceExporter = RecordingExporter()
    platform = create_test_platform(
        run_dir,
        ai_provider=ai_provider,
        instrumentation_enabled=True,
        exporter=exporter,
    )
    assert isinstance(exporter, RecordingExporter)
    return platform, exporter
