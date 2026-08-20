# Atlas eval report -- 20260819T122908Z

This is a real, unmodified report from `uv run python -m evals`, committed so
the eval layer's output is visible without running anything. It is also the
run currently tracked as the baseline at `evals/baselines/latest.json` --
regression detection on the next run diffs against exactly this one.

Generated: 2026-08-19T12:31:00.785363+00:00
Provider: OLLAMA:qwen2.5-coder:7b (local, no cloud API)

## Summary

- **Pass rate: 100%** (22/22 tasks)
- Latency p50 / p95: 1ms / 12515ms
- Total tokens: 8990 (prompt 7469 / completion 1521)
- Total estimated cost: not tracked (no pricing table -- see the Step 1 plan)

## Pass rate by category

| | pass rate |
|---|---|
| error_handling | 100% |
| hallucination_check | 100% |
| multi_step | 100% |
| schema_correctness | 100% |
| tool_selection | 100% |

## Pass rate by adapter

| | pass rate |
|---|---|
| ai | 100% |
| cli | 100% |
| ide | 100% |
| mcp | 100% |
| rest | 100% |

## Task results

| task_id | adapter | category | result | failures |
|---|---|---|---|---|
| cli-001-create-project | cli | tool_selection | PASS |  |
| cli-002-list-projects-empty | cli | schema_correctness | PASS |  |
| cli-003-workflow-status-after-transition | cli | tool_selection | PASS |  |
| mcp-001-transition-stage | mcp | tool_selection | PASS |  |
| mcp-002-execute-research-stage | mcp | multi_step | PASS |  |
| mcp-003-list-knowledge-candidates-empty | mcp | schema_correctness | PASS |  |
| ide-001-archive-project | ide | tool_selection | PASS |  |
| ide-002-load-project-round-trip | ide | schema_correctness | PASS |  |
| ide-003-review-nonexistent-knowledge-candidate | ide | error_handling | PASS |  |
| rest-001-create-project-full-fields | rest | schema_correctness | PASS |  |
| rest-002-approve-nonexistent-proposal | rest | error_handling | PASS |  |
| rest-003-reject-nonexistent-proposal | rest | error_handling | PASS |  |
| schema-001-error-envelope-shape | rest | schema_correctness | PASS |  |
| tool-001-execute-stage-invokes-workflow-execution-and-ai | ai | tool_selection | PASS |  |
| err-001-load-nonexistent-project | mcp | error_handling | PASS |  |
| hall-001-unknown-command-type | ai | hallucination_check | PASS |  |
| hall-002-hallucinated-extra-field-is-silently-dropped | ai | hallucination_check | PASS |  |
| hall-003-invalid-enum-value-rejected-before-reaching-atlas | ai | hallucination_check | PASS |  |
| hall-004-missing-required-field-rejected-before-reaching-atlas | ai | hallucination_check | PASS |  |
| multi-001-research-to-planning-pipeline | ai | multi_step | PASS |  |
| multi-002-reject-then-retry-recovery | ai | multi_step | PASS |  |
| multi-003-knowledge-lookup-then-archive-lifecycle | ide | multi_step | PASS |  |

## Notes on reading these numbers

- **Adapter tags are envelope identity, not live transports.** Only the CLI
  adapter is actually implemented in `clients/`; MCP/REST/IDE are documented
  stubs. Every task here drives `Atlas.handle()` directly with an
  `AdapterContext` tagged for the adapter it represents -- the same
  adapter-agnostic contract those transports will eventually sit on top of.
  See `evals/tasks/benchmark.yaml`'s header for the full rationale.
- **Latency p95 (12.5s) is dominated by real local-model generation**, not
  platform overhead -- non-AI tasks resolve in low single-digit milliseconds
  (p50 of 1ms reflects that most of the 22 tasks never touch the model).
- **A later run against this same baseline caught a real regression**
  (`multi-002-reject-then-retry-recovery` failed on model non-determinism on
  retry) -- see `docs/evaluations.md` for that walkthrough. This file is the
  clean baseline run, not that one.
