"""Builds a real, fully-wired Atlas platform for an eval run.

Reuses ``tests.support.test_bootstrap.create_test_platform`` rather than
duplicating its ~150 lines of production-shaped service wiring: it already
supports everything an eval run needs (real repositories/services, an
injectable AIProvider, an injectable workspace root, an injectable
TraceExporter) and is exercised by Step 1's own test suite. This is
dev/eval tooling, not a production client adapter -- importing test support
code here (rather than into ``atlas``/``engine``) keeps that boundary
intact while avoiding a near-duplicate second bootstrap implementation.
"""

from __future__ import annotations

from pathlib import Path

from atlas import Atlas
from atlas.observability.exporter import TraceExporter
from atlas.observability.models import TraceRecord
from engine.ai.provider import AIProvider
from tests.support.test_bootstrap import create_test_platform


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

    ``run_dir`` is the eval run's own directory; ``create_test_platform``
    creates ``run_dir / "workspace"`` under it (matching its ``tmp_path``
    convention from tests) via a bare ``mkdir()`` with no ``parents=True``,
    so ``run_dir`` itself must already exist -- ensured here rather than
    relying on every caller to remember it.
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
