"""Eval runner CLI: `uv run python -m evals [options]`.

Runs the benchmark task suite against a real Atlas platform wired to a real
AI provider (Ollama by default -- no mock provider path here; this command
is for actual eval runs, not the runner's own unit tests, which use
MockAIProvider under tests/evals/).

Also diffs the run against the most recent stored baseline (see
evals/baseline.py) and prints a regression summary. Pass --update-baseline
to promote this run to the new baseline regardless of outcome.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from engine.ai.config import ProviderConfig
from engine.ai.factory import ProtocolFactory
from evals.baseline import (
    Baseline,
    RegressionFinding,
    diff_against_baseline,
    load_baseline,
    save_baseline,
    snapshot_tasks,
)
from evals.loader import load_tasks
from evals.platform import build_eval_platform
from evals.report import Report, build_report, write_json, write_markdown
from evals.results import TaskResult
from evals.runner import run_task
from evals.schema import TaskSpec

_DEFAULT_BASELINE_PATH = Path("evals/baselines/latest.json")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Atlas benchmark task suite.")
    parser.add_argument(
        "--tasks", type=Path, default=Path("evals/tasks/benchmark.yaml")
    )
    parser.add_argument("--out-dir", type=Path, default=Path("evals/runs"))
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.90,
        help="Minimum pass rate to exit 0 (default: 0.90).",
    )
    parser.add_argument("--ai-protocol", default="OLLAMA")
    parser.add_argument("--ai-model", default="qwen2.5-coder:7b")
    parser.add_argument("--ai-endpoint", default="http://localhost:11434")
    parser.add_argument("--ai-timeout-seconds", type=int, default=120)
    parser.add_argument("--baseline-path", type=Path, default=_DEFAULT_BASELINE_PATH)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Promote this run to the new baseline, regardless of outcome.",
    )
    return parser.parse_args(argv)


def _write_line(line: str = "") -> None:
    sys.stdout.write(line + "\n")


def _write_summary(report: Report, run_dir: Path) -> None:
    _write_line()
    _write_line(
        f"Pass rate: {report.pass_rate:.0%} "
        f"({report.passed_tasks}/{report.total_tasks})"
    )
    _write_line(f"Latency p50/p95: {report.latency_p50_ms}/{report.latency_p95_ms} ms")
    _write_line(f"Total tokens: {report.total_tokens}")
    _write_line(f"Report: {run_dir / 'report.md'}")
    _write_line(f"Report: {run_dir / 'report.json'}")


def _write_regressions(findings: list[RegressionFinding], baseline: Baseline) -> None:
    _write_line()
    if not findings:
        _write_line(f"No regressions vs. baseline {baseline.run_id!r}.")
        return
    _write_line(f"Regressions vs. baseline {baseline.run_id!r}:")
    for finding in findings:
        _write_line(f"  [{finding.kind}] {finding.task_id}: {finding.detail}")


def _run_all_tasks(
    args: argparse.Namespace, run_dir: Path, tasks: list[TaskSpec]
) -> list[TaskResult]:
    provider_config = ProviderConfig(
        protocol=args.ai_protocol,
        model=args.ai_model,
        endpoint=args.ai_endpoint,
        timeout_seconds=args.ai_timeout_seconds,
    )
    ai_provider = ProtocolFactory().create(args.ai_protocol, provider_config)

    task_results = []
    for i, task in enumerate(tasks, 1):
        # A fresh platform per task: tasks share generic names ("P", etc.)
        # by design, and a shared platform lets one task's leftover state
        # (e.g. a same-named project) break an unrelated task -- confirmed
        # directly (FilesystemProjectRepository.save() raises
        # ProjectAlreadyExistsException on a slug collision between two
        # different projects). Cheap: it's in-memory service construction,
        # not a network call.
        platform, exporter = build_eval_platform(
            run_dir / "tasks" / task.task_id, ai_provider
        )
        result = run_task(platform, task, exporter, ai_provider)
        status = "PASS" if result.passed else "FAIL"
        _write_line(f"[{i}/{len(tasks)}] {task.task_id} ... {status}")
        for failure in result.failures:
            _write_line(f"    {failure}")
        task_results.append(result)
    return task_results


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    tasks = load_tasks(args.tasks)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    task_results = _run_all_tasks(args, run_dir, tasks)

    report = build_report(run_id, f"{args.ai_protocol}:{args.ai_model}", task_results)
    write_json(report, run_dir / "report.json")
    write_markdown(report, run_dir / "report.md")
    _write_summary(report, run_dir)

    current = snapshot_tasks(run_id, task_results)
    baseline = load_baseline(args.baseline_path)
    findings: list[RegressionFinding] = []
    if baseline is not None:
        findings = diff_against_baseline(current, baseline)
        _write_regressions(findings, baseline)
    else:
        _write_line()
        _write_line(f"No baseline at {args.baseline_path} yet -- nothing to diff.")

    if args.update_baseline:
        save_baseline(current, args.baseline_path)
        _write_line(f"Baseline updated: {args.baseline_path}")

    return 0 if report.pass_rate >= args.threshold and not findings else 1


if __name__ == "__main__":
    sys.exit(main())
