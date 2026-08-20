"""Executes one TaskSpec's steps, in order, against a live Atlas platform."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from atlas import Atlas
from atlas.adapters.protocol import AdapterContext, AdapterKind
from atlas.commands import Command
from atlas.contracts.envelope import RequestEnvelope
from engine.ai.provider import AIProvider
from evals.commands import resolve_command_class
from evals.platform import RecordingExporter
from evals.results import StepResult, TaskResult
from evals.schema import CommandSpec, Outcome, StepSpec, TaskSpec
from evals.scoring import score_step
from evals.substitution import resolve_path, substitute

_RUNNER_ADAPTER_NAME = "atlas-eval-runner"
_RUNNER_ADAPTER_VERSION = "0.1.0"


def construct_command(spec: CommandSpec, context: dict[str, Any]) -> Command:
    command_class = resolve_command_class(spec.type)
    fields = substitute(spec.fields, context)
    return command_class(**fields)


def run_task(
    platform: Atlas,
    task: TaskSpec,
    exporter: RecordingExporter,
    ai_provider: AIProvider,
) -> TaskResult:
    context: dict[str, Any] = {}
    step_results: list[StepResult] = []

    for step in task.as_steps():
        step_result = _run_step(platform, task, step, exporter, ai_provider, context)
        step_results.append(step_result)
        if not step_result.passed:
            # Stop the chain: later steps almost always depend on state this
            # one was supposed to establish (e.g. a captured project_id).
            break

    passed = len(step_results) == len(task.as_steps()) and all(
        sr.passed for sr in step_results
    )
    return TaskResult(
        task_id=task.task_id,
        description=task.description,
        adapter=task.adapter,
        category=task.category,
        passed=passed,
        step_results=tuple(step_results),
    )


def _run_step(  # noqa: PLR0913
    platform: Atlas,
    task: TaskSpec,
    step: StepSpec,
    exporter: RecordingExporter,
    ai_provider: AIProvider,
    context: dict[str, Any],
) -> StepResult:
    if step.ai_response is not None and hasattr(ai_provider, "stubbed_response"):
        ai_provider.stubbed_response = step.ai_response

    try:
        command = construct_command(step.command, context)
    except ValidationError:
        failures = score_step(step.expected, "validation_error", None, None, context)
        return StepResult(
            passed=not failures, failures=tuple(failures), trace_record=None
        )

    envelope = RequestEnvelope(
        adapter=AdapterContext(
            kind=AdapterKind(task.adapter),
            name=_RUNNER_ADAPTER_NAME,
            version=_RUNNER_ADAPTER_VERSION,
        ),
        command=command,
    )
    exported_before = len(exporter.records)
    response = platform.handle(envelope)
    trace_record = (
        exporter.records[-1] if len(exporter.records) > exported_before else None
    )
    actual_outcome: Outcome = "error" if response.error is not None else "success"
    context["request_id"] = envelope.request_id

    # Only attempt capture on a successful response -- a None `result` on an
    # error response makes any path meaningless, and a real model's failure
    # (bad JSON, a real error) must degrade to a clean scoring failure, not
    # crash the whole run. Wrapped even on success since a step's own
    # `capture` path could still reference a field that doesn't exist.
    if response.error is None:
        try:
            for name, path in step.capture.items():
                context[name] = resolve_path(response, path)
        except Exception as exc:
            return StepResult(
                passed=False,
                failures=(f"capture failed: {exc}",),
                trace_record=trace_record,
            )

    failures = score_step(
        step.expected, actual_outcome, response, trace_record, context
    )
    return StepResult(
        passed=not failures, failures=tuple(failures), trace_record=trace_record
    )
