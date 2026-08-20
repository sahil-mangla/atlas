"""Result types produced by running one task through the eval runner."""

from __future__ import annotations

from dataclasses import dataclass, field

from atlas.observability.models import TraceRecord


@dataclass(frozen=True)
class StepResult:
    passed: bool
    failures: tuple[str, ...]
    trace_record: TraceRecord | None


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    description: str
    adapter: str
    category: str
    passed: bool
    step_results: tuple[StepResult, ...] = field(default_factory=tuple)

    @property
    def failures(self) -> tuple[str, ...]:
        return tuple(
            f"step {i}: {failure}"
            for i, step in enumerate(self.step_results)
            for failure in step.failures
        )

    @property
    def trace_records(self) -> tuple[TraceRecord, ...]:
        return tuple(
            step.trace_record
            for step in self.step_results
            if step.trace_record is not None
        )
