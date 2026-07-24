# Multi-Protocol AI Runtime

`PromptExecutor` depends only on `AIProvider`. Protocol resolution occurs once
in bootstrap: `ProviderConfig` → `ProtocolFactory` → protocol adapter.

The immutable protocol registry inside `ProtocolFactory` includes `GEMINI`,
`OPENAI_COMPATIBLE`, `ANTHROPIC`, and `OLLAMA`. Adapters exclusively own request
normalization, response normalization, and truthful `ProviderCapabilities`
metadata for behavior implemented today.

Runtime settings use `ATLAS_AI_PROTOCOL`, `ATLAS_AI_ENDPOINT`,
`ATLAS_AI_MODEL`, and `ATLAS_AI_API_KEY`. Legacy Gemini settings remain
compatible.

`PromptExecutor` fails explicitly when a request requires a capability the
selected adapter does not implement. Capability flags must never advertise
unimplemented features.

## Structured Output (`response_schema`) Per Adapter

Each adapter that declares `structured_output=True` must actually constrain
generation to `AIRequest.response_schema`, not just request "some JSON":

- **Gemini** (default provider): `response_schema` is a raw Pydantic
  `model_json_schema()` dict, which uses `$defs`/`$ref` for any nested
  submodel (every non-trivial proposal draft has one -- e.g.
  `ResearchProposalDraft` nests `ResearchFindingDraft`/
  `ResearchEvidenceDraft`). `engine/ai/adapters/gemini.py::_flatten_schema`
  inlines every `$ref` against `$defs` before the schema reaches the SDK.
- **Ollama**: `/api/generate`'s `format` field accepts either the literal
  string `"json"` (any valid JSON) or a full JSON schema object (constrained
  to that shape). `engine/ai/adapters/ollama.py` forwards
  `request.response_schema` itself as `format`, not the generic string --
  otherwise the adapter's `structured_output=True` capability flag would be
  advertising more than it delivers, in violation of the "capability flags
  must never advertise unimplemented features" rule above.
- **Anthropic**: does not support schema-constrained output (`structured_output=False`
  per its `capabilities()`); response parsing selects the first content block
  that actually carries a `text` field rather than assuming `content[0]` is
  text, since a leading non-text block (e.g. a `thinking` block, reachable
  when extended-thinking options are merged into `self._config.options`)
  would otherwise silently produce an empty string.
- **OpenAI-compatible**: uses the OpenAI `response_format` JSON-schema
  mechanism directly; no flattening needed (see `tests/ai/test_protocol_runtime.py`).

## Extending Protocols and Vendors

To add a protocol:

1. Implement an `AIProvider` adapter in `engine/ai/adapters/`.
2. Register its constructor with `ProtocolFactory`.

To use another vendor that already implements a registered protocol (for
example any OpenAI-compatible endpoint), change only endpoint, model, and
credentials. No adapter or engineering workflow change is required.
