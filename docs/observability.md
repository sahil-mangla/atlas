# Observability

ATLAS instruments the versioned request boundary exposed by
`Atlas.handle()`. The boundary is the common doorway for envelope-based
clients, so request traces do not depend on whether the caller is an MCP,
REST, IDE, AI, or test adapter.

Named facade methods such as `create_project()` and `execute_stage()` are not
instrumented automatically. The CLI currently uses those named methods, while
the evaluation suite deliberately exercises the envelope boundary directly.

## Configuration

Instrumentation is enabled by default in the production composition root.
Disable it with:

```bash
export ATLAS_INSTRUMENTATION_ENABLED=false
```

The setting is read by `engine.config.Settings` and resolved once by
`atlas/_bootstrap.py`. Production bootstrap wires an enabled instance to
`JsonlFileExporter`; direct `Atlas(...)` construction defaults to
`NullExporter`, which avoids filesystem side effects in tests and SDK usage.

## Trace records

Each completed `Atlas.handle()` request produces one immutable `TraceRecord`
with:

| Field | Meaning |
|---|---|
| `request_id` | Envelope request identifier |
| `timestamp` | UTC time when handling began |
| `adapter` | Adapter kind carried by the envelope |
| `capability` | Capability selected by the command table, or `null` if unknown |
| `ai_provider` | Provider name when an AI call occurred |
| `latency_ms` | End-to-end request latency |
| `prompt_tokens`, `completion_tokens`, `total_tokens` | Aggregated AI usage for the request |
| `outcome` | `success` or `error` |
| `error_code` | Stable platform error code for returned errors, otherwise `null` |

AI usage is captured at the provider boundary in `engine.ai.executor` and
passed back to the request boundary through the `ContextVar` in
`shared.observability.usage_context`. This preserves the one-way dependency
direction: `engine` does not import `atlas`.

Returned `ResponseEnvelope` errors are traced with their platform error code.
Unexpected exceptions are also traced as `error` records and then re-raised
unchanged. An exporter failure is logged and swallowed so observability cannot
change application behavior.

## File export

The default exporter writes append-only JSONL files below:

```text
<workspace-root>/traces/YYYY-MM-DD.jsonl
```

There is one JSON object per line. For example:

```json
{"request_id":"...","timestamp":"2026-08-20T10:15:00Z","adapter":"ai","capability":"workflow_execution","ai_provider":"ollamaprovider","latency_ms":842.4,"prompt_tokens":1200,"completion_tokens":180,"total_tokens":1380,"cost_usd":null,"outcome":"success","error_code":null}
```

The exporter uses append mode and flushes plus `fsync`s each record. This
favors durability and simple recovery over maximum write throughput. Trace
records contain usage metadata, not prompt or completion content; treat the
trace directory as operational data and apply the host's normal access and
retention controls.

## Extension points

`TraceExporter` is a small protocol. A caller can provide an in-memory, remote,
or test exporter when constructing `Atlas`. Keep exporters non-blocking where
possible and never allow exporter exceptions to escape request handling.

The current schema reserves `TraceOutcome.TIMEOUT`, but timeout-specific
classification is not emitted yet because provider transport failures do not
currently distinguish timeouts from other provider errors.
