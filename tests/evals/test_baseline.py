"""Tests for regression detection: two synthetic runs, one with an injected
regression, confirming the diff logic catches it (and doesn't false-positive
on an unchanged run)."""

from pathlib import Path

from evals.baseline import (
    Baseline,
    TaskSnapshot,
    diff_against_baseline,
    load_baseline,
    save_baseline,
    snapshot_tasks,
)
from evals.results import StepResult, TaskResult


def _baseline_run() -> Baseline:
    return Baseline(
        run_id="run-1",
        tasks={
            "task-a": TaskSnapshot(
                task_id="task-a", passed=True, total_latency_ms=100.0, total_tokens=500
            ),
            "task-b": TaskSnapshot(
                task_id="task-b", passed=True, total_latency_ms=50.0, total_tokens=0
            ),
            "task-c": TaskSnapshot(
                task_id="task-c", passed=False, total_latency_ms=10.0, total_tokens=0
            ),
        },
    )


def test_identical_run_produces_no_regressions() -> None:
    baseline = _baseline_run()
    current = Baseline(run_id="run-2", tasks=dict(baseline.tasks))

    assert diff_against_baseline(current, baseline) == []


def test_pass_to_fail_is_flagged_as_regressed() -> None:
    baseline = _baseline_run()
    current = Baseline(
        run_id="run-2",
        tasks={
            **baseline.tasks,
            "task-a": TaskSnapshot(
                task_id="task-a", passed=False, total_latency_ms=100.0, total_tokens=500
            ),
        },
    )

    findings = diff_against_baseline(current, baseline)

    assert len(findings) == 1
    assert findings[0].task_id == "task-a"
    assert findings[0].kind == "regressed"


def test_fail_to_pass_is_not_a_regression() -> None:
    baseline = _baseline_run()
    current = Baseline(
        run_id="run-2",
        tasks={
            **baseline.tasks,
            "task-c": TaskSnapshot(
                task_id="task-c", passed=True, total_latency_ms=10.0, total_tokens=0
            ),
        },
    )

    assert diff_against_baseline(current, baseline) == []


def test_latency_increase_over_threshold_is_flagged() -> None:
    baseline = _baseline_run()
    current = Baseline(
        run_id="run-2",
        tasks={
            **baseline.tasks,
            # 100ms -> 130ms is +30%, over the 25% threshold.
            "task-a": TaskSnapshot(
                task_id="task-a", passed=True, total_latency_ms=130.0, total_tokens=500
            ),
        },
    )

    findings = diff_against_baseline(current, baseline)

    assert len(findings) == 1
    assert findings[0].task_id == "task-a"
    assert findings[0].kind == "latency"


def test_latency_increase_under_threshold_is_not_flagged() -> None:
    baseline = _baseline_run()
    current = Baseline(
        run_id="run-2",
        tasks={
            **baseline.tasks,
            # 100ms -> 110ms is +10%, under the 25% threshold.
            "task-a": TaskSnapshot(
                task_id="task-a", passed=True, total_latency_ms=110.0, total_tokens=500
            ),
        },
    )

    assert diff_against_baseline(current, baseline) == []


def test_token_increase_over_threshold_is_flagged() -> None:
    baseline = _baseline_run()
    current = Baseline(
        run_id="run-2",
        tasks={
            **baseline.tasks,
            # 500 -> 800 is +60%, over the 25% threshold.
            "task-a": TaskSnapshot(
                task_id="task-a", passed=True, total_latency_ms=100.0, total_tokens=800
            ),
        },
    )

    findings = diff_against_baseline(current, baseline)

    assert len(findings) == 1
    assert findings[0].task_id == "task-a"
    assert findings[0].kind == "tokens"


def test_zero_baseline_tokens_is_not_divided_by_zero() -> None:
    """task-b has 0 baseline tokens (no AI call) -- must not crash or flag."""
    baseline = _baseline_run()
    current = Baseline(
        run_id="run-2",
        tasks={
            **baseline.tasks,
            "task-b": TaskSnapshot(
                task_id="task-b", passed=True, total_latency_ms=50.0, total_tokens=5
            ),
        },
    )

    assert diff_against_baseline(current, baseline) == []


def test_task_missing_from_baseline_is_skipped_not_flagged() -> None:
    baseline = _baseline_run()
    current = Baseline(
        run_id="run-2",
        tasks={
            **baseline.tasks,
            "task-new": TaskSnapshot(
                task_id="task-new", passed=False, total_latency_ms=1.0, total_tokens=0
            ),
        },
    )

    assert diff_against_baseline(current, baseline) == []


def test_multiple_regressions_on_the_same_task_are_all_reported() -> None:
    baseline = _baseline_run()
    current = Baseline(
        run_id="run-2",
        tasks={
            **baseline.tasks,
            "task-a": TaskSnapshot(
                task_id="task-a", passed=False, total_latency_ms=200.0, total_tokens=900
            ),
        },
    )

    findings = diff_against_baseline(current, baseline)

    kinds = {f.kind for f in findings if f.task_id == "task-a"}
    assert kinds == {"regressed", "latency", "tokens"}


def test_snapshot_tasks_reduces_task_results() -> None:
    result = TaskResult(
        task_id="t",
        description="d",
        adapter="cli",
        category="tool_selection",
        passed=True,
        step_results=(StepResult(passed=True, failures=(), trace_record=None),),
    )

    snapshot = snapshot_tasks("run-1", [result])

    assert snapshot.tasks["t"].passed is True
    assert snapshot.tasks["t"].total_latency_ms == 0.0
    assert snapshot.tasks["t"].total_tokens == 0


def test_save_and_load_baseline_round_trips(tmp_path: Path) -> None:
    baseline = _baseline_run()
    path = tmp_path / "baselines" / "latest.json"

    save_baseline(baseline, path)
    loaded = load_baseline(path)

    assert loaded == baseline


def test_load_baseline_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_baseline(tmp_path / "does-not-exist.json") is None
