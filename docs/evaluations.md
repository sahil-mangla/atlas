# Evaluation and Regression Workflow

The `evals/` package provides a deterministic, task-driven benchmark for the
Atlas platform boundary. It complements unit tests by exercising realistic
command sequences and checking both the returned response and the trace
record emitted for that request.

## Run the benchmark

The runner uses Ollama by default and expects a local model named
`qwen2.5-coder:7b`:

```bash
uv run python -m evals
```

To use another provider or model:

```bash
uv run python -m evals \
  --ai-protocol OPENAI_COMPATIBLE \
  --ai-model my-model \
  --ai-endpoint http://localhost:1234/v1 \
  --ai-timeout-seconds 180
```

The runner writes timestamped reports to `evals/runs/`. These run artifacts
are ignored by Git. Each run contains `report.md`, `report.json`, and isolated
task workspaces.

The command exits non-zero when the pass rate is below the threshold (90% by
default) or when a regression is detected against the stored baseline.

## Baselines

The tracked file `evals/baselines/latest.json` stores the small per-task
snapshot used for regression comparison:

- pass/fail status;
- total request latency;
- total token usage.

After intentionally accepting a new result, promote it explicitly:

```bash
uv run python -m evals --update-baseline
```

The comparison ignores tasks that were added or removed since the baseline.
Latency and token changes must exceed both an absolute noise floor and a 25%
relative increase before they are reported. Cost comparison is not available
yet because provider pricing is not modeled.

## Task files

The default suite is `evals/tasks/benchmark.yaml`. A task has either one
`input` or an ordered `steps` list:

```yaml
- task_id: create-project
  description: Creates a project through the platform boundary.
  adapter: cli
  category: tool_selection
  input:
    command:
      type: CreateProjectCommand
      fields:
        name: Example
        description: Short description
        objective: Project objective
  expected:
    outcome: success
    capability: project
    result_type: ProjectResult
```

Multi-step tasks can capture a result value and substitute it into a later
command:

```yaml
steps:
  - command:
      type: CreateProjectCommand
      fields: {name: P, description: D, objective: O}
    capture: {project_id: result.id}
    expected: {outcome: success, capability: project}
  - command:
      type: GetWorkflowStatusCommand
      fields: {project_id: "$project_id"}
    expected: {outcome: success, capability: workflow}
```

Expected values can assert the response outcome, capability, AI provider,
platform error code, result type, or individual result fields using `equals`,
`non_empty`, and `type`. `ai_response` provides a deterministic JSON response
for mock-backed tests; the real benchmark runner uses the configured provider.

## Adapter tags and current scope

The `adapter` field is metadata on the envelope. The benchmark currently uses
the common `Atlas.handle()` boundary directly, so `mcp`, `rest`, and `ide`
tasks do not claim that those transport servers are already implemented. The
CLI is the only production client currently wired as a real transport, and it
uses named facade methods today.

The suite intentionally covers the platform's dispatch contract: capability
routing, response schemas, multi-step state, AI execution, error handling, and
unknown or hallucinated command inputs.

## Unit tests for the runner

The runner itself is tested without network calls or a real model:

```bash
python -m pytest -q tests/evals tests/observability tests/test_shared_observability_usage_context.py
```

Use the full development verification workflow before merging:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```
