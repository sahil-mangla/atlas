"""Tests for the task-file loader/schema."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.loader import load_tasks
from evals.schema import TaskFile

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BENCHMARK = _REPO_ROOT / "evals" / "tasks" / "benchmark.yaml"
_TINY_FIXTURE = Path(__file__).parent / "fixtures" / "tiny.yaml"


def test_real_benchmark_suite_loads_and_validates() -> None:
    tasks = load_tasks(_BENCHMARK)
    assert len(tasks) >= 20
    assert len(tasks) <= 30


def test_real_benchmark_suite_has_unique_task_ids() -> None:
    tasks = load_tasks(_BENCHMARK)
    ids = [t.task_id for t in tasks]
    assert len(ids) == len(set(ids))


def test_real_benchmark_suite_covers_every_required_adapter() -> None:
    tasks = load_tasks(_BENCHMARK)
    counts: dict[str, int] = {}
    for task in tasks:
        counts[task.adapter] = counts.get(task.adapter, 0) + 1
    for adapter in ("cli", "mcp", "ide", "rest"):
        assert counts.get(adapter, 0) >= 3, f"{adapter} has fewer than 3 tasks"


def test_real_benchmark_suite_has_at_least_three_hallucination_checks() -> None:
    tasks = load_tasks(_BENCHMARK)
    count = sum(1 for t in tasks if t.category == "hallucination_check")
    assert count >= 3


def test_tiny_fixture_loads() -> None:
    tasks = load_tasks(_TINY_FIXTURE)
    assert len(tasks) == 2


def test_task_requires_exactly_one_of_input_or_steps() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        TaskFile.model_validate(
            {
                "tasks": [
                    {
                        "task_id": "bad",
                        "description": "d",
                        "adapter": "cli",
                        "category": "tool_selection",
                    }
                ]
            }
        )


def test_check_requires_exactly_one_assertion_kind() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        TaskFile.model_validate(
            {
                "tasks": [
                    {
                        "task_id": "bad",
                        "description": "d",
                        "adapter": "cli",
                        "category": "tool_selection",
                        "input": {"type": "ListProjectsCommand", "fields": {}},
                        "expected": {
                            "outcome": "success",
                            "checks": [
                                {"field": "result.x", "equals": 1, "non_empty": True}
                            ],
                        },
                    }
                ]
            }
        )
