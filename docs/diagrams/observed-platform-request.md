# Observed Platform Request

This diagram shows how request instrumentation surrounds the existing platform
dispatch path and how AI token usage crosses the `atlas`/`engine` boundary.

```mermaid
flowchart LR
    Client[Envelope client] --> Handle[Atlas.handle]
    Handle --> Capture[Start request capture]
    Capture --> Dispatch[Dispatch command to capability]
    Dispatch --> Engine[Engine services]
    Engine --> Provider[AI provider, when needed]
    Provider -. token usage .-> Shared[shared.observability.usage_context]
    Shared -. aggregated usage .-> Capture
    Dispatch --> Response[ResponseEnvelope or exception]
    Response --> Record[TraceRecord]
    Capture --> Record
    Record --> Export[TraceExporter]
    Response --> Client
    Response -. unexpected exception re-raised .-> Client
```

The exporter is best-effort. A failure to write or forward a trace is logged but
does not replace the response or the original exception.
