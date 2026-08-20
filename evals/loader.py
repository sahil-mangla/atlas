"""Loads and validates evals/tasks/*.yaml into typed TaskSpec objects."""

from __future__ import annotations

from pathlib import Path

import yaml

from evals.schema import TaskFile, TaskSpec


def load_tasks(path: Path) -> list[TaskSpec]:
    """Parse a benchmark task file, raising on any structural error."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return TaskFile.model_validate(raw).tasks
