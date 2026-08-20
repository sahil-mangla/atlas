"""Regression detection: snapshot a run's per-task results and diff against
the most recently stored baseline.

Cost regression is deliberately not checked: `cost_usd` is always None (no
pricing table -- see the Step 1 plan), so there is nothing to compare.

A pure percentage threshold blows up on near-zero baselines: a trivial,
non-AI request going from 0ms to 1ms is a meaningless "infinite" percent
increase, not a real regression -- confirmed directly by an early real run,
where seven non-AI tasks were flagged purely from sub-millisecond dispatch
noise. Each metric therefore also needs its absolute change to clear a
small floor before a percentage is even considered.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from evals.results import TaskResult

REGRESSION_THRESHOLD = 0.25  # a >25% increase counts as a regression
_LATENCY_MIN_DELTA_MS = 5.0
_TOKENS_MIN_DELTA = 20.0


@dataclass(frozen=True)
class TaskSnapshot:
    task_id: str
    passed: bool
    total_latency_ms: float
    total_tokens: int


@dataclass(frozen=True)
class Baseline:
    run_id: str
    tasks: dict[str, TaskSnapshot]


@dataclass(frozen=True)
class RegressionFinding:
    task_id: str
    kind: str  # "regressed" | "latency" | "tokens"
    detail: str


def snapshot_tasks(run_id: str, task_results: list[TaskResult]) -> Baseline:
    """Reduce a run's TaskResults to the small set of fields regression
    detection cares about, keyed by task_id."""
    tasks = {
        result.task_id: TaskSnapshot(
            task_id=result.task_id,
            passed=result.passed,
            total_latency_ms=sum(tr.latency_ms for tr in result.trace_records),
            total_tokens=sum(tr.total_tokens or 0 for tr in result.trace_records),
        )
        for result in task_results
    }
    return Baseline(run_id=run_id, tasks=tasks)


def load_baseline(path: Path) -> Baseline | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    tasks = {
        task_id: TaskSnapshot(**snapshot) for task_id, snapshot in data["tasks"].items()
    }
    return Baseline(run_id=data["run_id"], tasks=tasks)


def save_baseline(baseline: Baseline, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "run_id": baseline.run_id,
        "tasks": {
            task_id: {
                "task_id": snapshot.task_id,
                "passed": snapshot.passed,
                "total_latency_ms": snapshot.total_latency_ms,
                "total_tokens": snapshot.total_tokens,
            }
            for task_id, snapshot in baseline.tasks.items()
        },
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def diff_against_baseline(
    current: Baseline, baseline: Baseline, threshold: float = REGRESSION_THRESHOLD
) -> list[RegressionFinding]:
    """Compare `current` to `baseline`, task-by-task.

    Tasks present in only one of the two (a task added or removed since the
    baseline was captured) are silently skipped -- there is nothing to
    regress against.
    """
    findings: list[RegressionFinding] = []
    for task_id, now in current.tasks.items():
        before = baseline.tasks.get(task_id)
        if before is None:
            continue

        if before.passed and not now.passed:
            findings.append(
                RegressionFinding(
                    task_id=task_id,
                    kind="regressed",
                    detail=f"passed in baseline {baseline.run_id!r}, now fails",
                )
            )

        for kind, unit, before_v, now_v, min_delta in (
            (
                "latency",
                "ms",
                before.total_latency_ms,
                now.total_latency_ms,
                _LATENCY_MIN_DELTA_MS,
            ),
            ("tokens", "", before.total_tokens, now.total_tokens, _TOKENS_MIN_DELTA),
        ):
            increase = _percent_increase(before_v, now_v, threshold, min_delta)
            if increase is not None:
                findings.append(
                    RegressionFinding(
                        task_id=task_id,
                        kind=kind,
                        detail=(
                            f"{kind} +{increase:.0%} "
                            f"({before_v:.0f}{unit} -> {now_v:.0f}{unit})"
                        ),
                    )
                )

    return findings


def _percent_increase(
    before: float, now: float, threshold: float, min_absolute_delta: float
) -> float | None:
    """Return the fractional increase from `before` to `now` if it exceeds
    `threshold`, else None -- including when `before` is 0 (nothing to
    divide by) or the absolute change hasn't cleared `min_absolute_delta`
    (too small to be signal rather than noise, regardless of what that
    looks like as a percentage of a tiny baseline)."""
    if before <= 0 or abs(now - before) < min_absolute_delta:
        return None
    increase = (now - before) / before
    return increase if increase > threshold else None
