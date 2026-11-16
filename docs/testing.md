# Testing Without an AI Provider

Everything in this repository can be tested with no API key, no local model
and no network access. This page describes the layers and how to run them.

## The SCRIPTED protocol

`ATLAS_AI_PROTOCOL=SCRIPTED` selects a deterministic, offline provider
(`atlas_eng/engine/ai/adapters/scripted.py`). It returns a fixed, schema-valid draft for
every stage, swaps the paper sources for a labelled fixture source, and
provides a hashed bag-of-words embedder.

```bash
export ATLAS_AI_PROTOCOL=SCRIPTED
atlas project create --name Demo --description "..." --objective "..."
atlas workflow transition --project-id <id> --reason "start"
atlas stage execute --project-id <id> --stage research
```

The output is canned demonstration text, not model output. Research evidence
produced this way is titled `[Demo fixture]` and points at the reserved
`.invalid` domain so it cannot be mistaken for real literature. Use SCRIPTED to
check that the pipeline works; use a real provider to judge what it produces.

Setting `ATLAS_AI_MODEL` to one of the following makes the scripted provider
fail in a specific way, for testing error handling:

| `ATLAS_AI_MODEL` | Behaviour |
|---|---|
| `malformed-json` | Returns prose instead of JSON |
| `schema-violation` | Returns JSON that does not match the schema |
| `truncated` | Returns the first half of a valid response |
| `provider-error` | Raises a provider error before responding |

## Test layers

| Layer | Location | What it proves |
|---|---|---|
| Unit and service tests | `tests/<subsystem>/` | Domain rules, services, repositories |
| Scripted provider | `tests/ai/test_scripted.py` | Every prompt template has a valid offline draft |
| Loopback HTTP | `tests/ai/test_http_loopback.py` | Adapters send and parse real HTTP, including 401/429/5xx, bad bodies and timeouts, against a fake server on 127.0.0.1 |
| Black-box CLI | `tests/blackbox/` | The `atlas` command, run as a subprocess in an empty directory, completes the pipeline and fails cleanly |
| Fault injection | `tests/test_atlas/test_fault_injection.py` | A disk failure during approval |
| Offline evals | `python -m evals --ai-protocol SCRIPTED` | Routing, schemas, errors and multi-step workflows through `Atlas.handle()` |
| Installed package | `scripts/smoke_installed.py` | A wheel installed in a clean environment runs the pipeline |

```bash
uv run pytest                                   # all pytest layers
uv run python -m evals --ai-protocol SCRIPTED --ai-model scripted \
  --baseline-path evals/baselines/scripted.json --no-latency-check
```

## Network is blocked in tests

`pytest` runs with `--disable-socket` (see `pyproject.toml`); only loopback is
allowed. A test that reaches a real service fails instead of passing by
accident. The black-box tests go further: each CLI subprocess runs with a
`sitecustomize` that blocks and logs every connection attempt, so a network
call is caught even if the application swallows the error.

## Writing tests against the platform

`atlas_eng.testing.create_test_platform` builds a real `Atlas` on a temporary
directory with the scripted provider:

```python
from atlas_eng.testing import create_test_platform

platform = create_test_platform(tmp_path)
```

Pass `ai_provider=ScriptedAIProvider(stubbed_response=...)` to drive one
specific model response through the real pipeline.

## Known failures

Tests marked `xfail(strict=True)` document bugs that are confirmed but not yet
fixed. They fail the build if the bug disappears, so the marker is removed
with the fix. Run `uv run pytest -rx` to list them.

## What this does not cover

- **Model quality.** Scripted output says nothing about how a real model
  performs. Run `python -m evals` against Ollama or a hosted model for that.
- **Provider drift.** The loopback server speaks each provider's format as the
  adapters understand it today. A provider changing its API is only caught by
  a run against the real service.
- **Gemini transport.** The Gemini adapter uses Google's SDK rather than plain
  HTTP, so it is covered by mocks only.
