"""Tests for TraceExporter implementations."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from atlas.adapters.protocol import AdapterKind
from atlas.capabilities.base import CapabilityName
from atlas.observability.exporter import JsonlFileExporter, NullExporter
from atlas.observability.models import TraceOutcome, TraceRecord


def _record(timestamp: datetime | None = None) -> TraceRecord:
    return TraceRecord(
        request_id=uuid4(),
        timestamp=timestamp or datetime.now(UTC),
        adapter=AdapterKind.AI,
        capability=CapabilityName.PROJECT,
        latency_ms=1.0,
        outcome=TraceOutcome.SUCCESS,
    )


def test_null_exporter_does_nothing() -> None:
    NullExporter().export(_record())


def test_jsonl_exporter_creates_directory_and_writes_one_line(tmp_path: Path) -> None:
    directory = tmp_path / "traces"
    exporter = JsonlFileExporter(directory)
    record = _record(timestamp=datetime(2026, 8, 19, tzinfo=UTC))

    exporter.export(record)

    path = directory / "2026-08-19.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["request_id"] == str(record.request_id)


def test_jsonl_exporter_appends_rather_than_overwrites(tmp_path: Path) -> None:
    exporter = JsonlFileExporter(tmp_path)
    same_day = datetime(2026, 8, 19, tzinfo=UTC)

    exporter.export(_record(timestamp=same_day))
    exporter.export(_record(timestamp=same_day))

    lines = (tmp_path / "2026-08-19.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_jsonl_exporter_writes_separate_files_per_day(tmp_path: Path) -> None:
    exporter = JsonlFileExporter(tmp_path)

    exporter.export(_record(timestamp=datetime(2026, 8, 19, tzinfo=UTC)))
    exporter.export(_record(timestamp=datetime(2026, 8, 20, tzinfo=UTC)))

    assert (tmp_path / "2026-08-19.jsonl").exists()
    assert (tmp_path / "2026-08-20.jsonl").exists()


def test_jsonl_exporter_leaves_no_temp_files_behind(tmp_path: Path) -> None:
    """Confirms this does NOT use atomic_write_text's tempfile+replace pattern."""
    exporter = JsonlFileExporter(tmp_path)

    exporter.export(_record(timestamp=datetime(2026, 8, 19, tzinfo=UTC)))

    entries = list(tmp_path.iterdir())
    assert entries == [tmp_path / "2026-08-19.jsonl"]
