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

## Extending Protocols and Vendors

To add a protocol:

1. Implement an `AIProvider` adapter in `engine/ai/adapters/`.
2. Register its constructor with `ProtocolFactory`.

To use another vendor that already implements a registered protocol (for
example any OpenAI-compatible endpoint), change only endpoint, model, and
credentials. No adapter or engineering workflow change is required.
