# Platform Request Dispatch Diagram (Phase 15)

This diagram shows the two valid paths through the Phase 15 platform layer: the permanent named-method path (in-process callers, e.g. the CLI) and the preferred envelope path (out-of-process/protocol adapters, e.g. MCP, REST, IDE, AI agents).

```mermaid
flowchart TD
    classDef client fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px;
    classDef contract fill:#fff3e0,stroke:#ff9800,stroke-width:2px;
    classDef capability fill:#e8f5e9,stroke:#4caf50,stroke-width:2px;
    classDef engine fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px;

    CLI([CLI Adapter]):::client
    MCP([MCP / REST / IDE / AI Agent]):::client

    CLI -->|"Atlas.&lt;named method&gt;(Command) -> Result (permanent)"| Atlas
    MCP -->|"Atlas.handle(RequestEnvelope) -> ResponseEnvelope (preferred)"| Handle["Atlas.handle()"]:::contract

    Handle -->|"_dispatch lookup by type(command)"| Atlas["Atlas Facade"]

    subgraph CapabilityLayer["Capability Layer (atlas/capabilities/)"]
        Project[ProjectCapability]:::capability
        Workflow[WorkflowCapability]:::capability
        WorkflowExec[WorkflowExecutionCapability]:::capability
        Knowledge[KnowledgeCapability]:::capability
        Presentation[PresentationCapability]:::capability
    end

    Atlas --> Project
    Atlas --> Workflow
    Atlas --> WorkflowExec
    Atlas --> Knowledge
    Atlas --> Presentation

    subgraph EngineServices["Existing Phase 1-14 Services (unchanged)"]
        ProjSvc[Project Services]:::engine
        WorkflowOrch[WorkflowOrchestrationService]:::engine
        KnowledgeOrch[KnowledgeOrchestrationService]:::engine
        PlatformOrch[PlatformOrchestrationService]:::engine
    end

    Project --> ProjSvc
    Workflow --> WorkflowOrch
    WorkflowExec --> WorkflowOrch
    Knowledge --> WorkflowOrch
    Knowledge --> KnowledgeOrch
    Presentation --> PlatformOrch

    Handle -.->|"ApplicationError -> ErrorEnvelope via to_error_envelope()"| ErrorPath["ResponseEnvelope.error"]:::contract
    Atlas -.->|Result| CLI
    Handle -.->|"ResponseEnvelope.result"| MCP
```

## Notes

- The named-method path (left) is unchanged from Phase 1-14 and remains permanently supported -- it is not a deprecated shim.
- `Atlas.handle()` is new in Phase 15. It looks up the exact `Command` subclass in an explicit literal `_dispatch` dict (ten entries), calls the matching capability method, and wraps the result (or a caught `ApplicationError`, via `to_error_envelope()`) in a `ResponseEnvelope`.
- Every capability delegates to the same engine services `Atlas` always used -- no new engine surface area is reachable through this diagram.

See also [Application Platform Diagram](application-platform.md), [Client Adapter Layer Diagram](client-adapter-layer.md), and the [Platform Layer architecture doc](../architecture/platform-layer.md).
