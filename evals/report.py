"""Aggregates TaskResults into a report and writes JSON + Markdown."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from evals.results import TaskResult


@dataclass(frozen=True)
class Report:
    run_id: str
    generated_at: datetime
    provider_label: str
    total_tasks: int
    passed_tasks: int
    pass_rate: float
    pass_rate_by_category: dict[str, float]
    pass_rate_by_adapter: dict[str, float]
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost_usd: None
    task_results: tuple[TaskResult, ...]


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(pct * (len(ordered) - 1))))
    return ordered[index]


def _pass_rate_by(task_results: tuple[TaskResult, ...], key: str) -> dict[str, float]:
    totals: dict[str, int] = defaultdict(int)
    passed: dict[str, int] = defaultdict(int)
    for result in task_results:
        bucket = getattr(result, key)
        totals[bucket] += 1
        if result.passed:
            passed[bucket] += 1
    return {bucket: passed[bucket] / totals[bucket] for bucket in totals}


def build_report(
    run_id: str, provider_label: str, task_results: list[TaskResult]
) -> Report:
    results = tuple(task_results)
    passed = sum(1 for r in results if r.passed)
    latencies = [tr.latency_ms for r in results for tr in r.trace_records]
    prompt_tokens = sum(
        tr.prompt_tokens or 0 for r in results for tr in r.trace_records
    )
    completion_tokens = sum(
        tr.completion_tokens or 0 for r in results for tr in r.trace_records
    )

    return Report(
        run_id=run_id,
        generated_at=datetime.now(UTC),
        provider_label=provider_label,
        total_tasks=len(results),
        passed_tasks=passed,
        pass_rate=passed / len(results) if results else 0.0,
        pass_rate_by_category=_pass_rate_by(results, "category"),
        pass_rate_by_adapter=_pass_rate_by(results, "adapter"),
        latency_p50_ms=_percentile(latencies, 0.50) if latencies else None,
        latency_p95_ms=_percentile(latencies, 0.95) if latencies else None,
        total_prompt_tokens=prompt_tokens,
        total_completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        total_cost_usd=None,
        task_results=results,
    )


def _task_result_to_dict(result: TaskResult) -> dict[str, object]:
    return {
        "task_id": result.task_id,
        "description": result.description,
        "adapter": result.adapter,
        "category": result.category,
        "passed": result.passed,
        "failures": list(result.failures),
        "steps": [
            {
                "passed": step.passed,
                "failures": list(step.failures),
                "trace_record": (
                    step.trace_record.model_dump(mode="json")
                    if step.trace_record is not None
                    else None
                ),
            }
            for step in result.step_results
        ],
    }


def to_json_dict(report: Report) -> dict[str, object]:
    return {
        "run_id": report.run_id,
        "generated_at": report.generated_at.isoformat(),
        "provider_label": report.provider_label,
        "total_tasks": report.total_tasks,
        "passed_tasks": report.passed_tasks,
        "pass_rate": report.pass_rate,
        "pass_rate_by_category": report.pass_rate_by_category,
        "pass_rate_by_adapter": report.pass_rate_by_adapter,
        "latency_p50_ms": report.latency_p50_ms,
        "latency_p95_ms": report.latency_p95_ms,
        "total_prompt_tokens": report.total_prompt_tokens,
        "total_completion_tokens": report.total_completion_tokens,
        "total_tokens": report.total_tokens,
        "total_cost_usd": report.total_cost_usd,
        "task_results": [_task_result_to_dict(r) for r in report.task_results],
    }


def write_json(report: Report, path: Path) -> None:
    path.write_text(json.dumps(to_json_dict(report), indent=2), encoding="utf-8")


def _pct_table(rates: dict[str, float]) -> str:
    lines = ["| | pass rate |", "|---|---|"]
    for key in sorted(rates):
        lines.append(f"| {key} | {rates[key]:.0%} |")
    return "\n".join(lines)


def to_markdown(report: Report) -> str:
    lines = [
        f"# Atlas eval report -- {report.run_id}",
        "",
        f"Generated: {report.generated_at.isoformat()}  ",
        f"Provider: {report.provider_label}",
        "",
        "## Summary",
        "",
        f"- **Pass rate: {report.pass_rate:.0%}** "
        f"({report.passed_tasks}/{report.total_tasks} tasks)",
        f"- Latency p50 / p95: "
        f"{_fmt_ms(report.latency_p50_ms)} / {_fmt_ms(report.latency_p95_ms)}",
        f"- Total tokens: {report.total_tokens} "
        f"(prompt {report.total_prompt_tokens} / "
        f"completion {report.total_completion_tokens})",
        "- Total estimated cost: not tracked (no pricing table -- see plan)",
        "",
        "## Pass rate by category",
        "",
        _pct_table(report.pass_rate_by_category),
        "",
        "## Pass rate by adapter",
        "",
        _pct_table(report.pass_rate_by_adapter),
        "",
        "## Task results",
        "",
        "| task_id | adapter | category | result | failures |",
        "|---|---|---|---|---|",
    ]
    for result in report.task_results:
        status = "PASS" if result.passed else "FAIL"
        failure_text = "; ".join(result.failures) if result.failures else ""
        lines.append(
            f"| {result.task_id} | {result.adapter} | {result.category} "
            f"| {status} | {failure_text} |"
        )
    return "\n".join(lines) + "\n"


def _fmt_ms(value: float | None) -> str:
    return f"{value:.0f}ms" if value is not None else "n/a"


def write_markdown(report: Report, path: Path) -> None:
    path.write_text(to_markdown(report), encoding="utf-8")
