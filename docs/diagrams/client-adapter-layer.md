# Client Adapter Layer Diagram

This diagram shows the relationship between external environments, the client adapters, and the public ATLAS SDK.

```mermaid
graph TD
    classDef external fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px;
    classDef adapter fill:#fff3e0,stroke:#ff9800,stroke-width:2px;
    classDef public_api fill:#e8f5e9,stroke:#4caf50,stroke-width:2px;
    classDef internal fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px;

    Term([Terminal User]):::external
    IDE([IDE User]):::external
    Agent([Agent/MCP]):::external
    HTTP([HTTP Client]):::external
    
    subgraph Client Adapters [Client Adapter Layer]
        CLI[CLI Adapter]:::adapter
        IDEAdapter[IDE Adapter]:::adapter
        MCPAdapter[MCP Adapter]:::adapter
        RESTAdapter[REST Adapter]:::adapter
        DesktopAdapter[Desktop Adapter]:::adapter
        
        Shared[clients/common]:::adapter
        
        CLI --> Shared
        IDEAdapter --> Shared
        MCPAdapter --> Shared
    end

    Term --> CLI
    IDE --> IDEAdapter
    Agent --> MCPAdapter
    HTTP --> RESTAdapter
    
    subgraph Core Platform
        Atlas[Atlas SDK / Facade]:::public_api
        Engine[ATLAS Engine Subsystems]:::internal
        
        Atlas --> Engine
    end
    
    CLI -->|"Command DTO (named method, permanent)"| Atlas
    IDEAdapter -->|"RequestEnvelope (Atlas.handle(), preferred)"| Atlas
    MCPAdapter -->|"RequestEnvelope (Atlas.handle(), preferred)"| Atlas
    RESTAdapter -->|"RequestEnvelope (Atlas.handle(), preferred)"| Atlas
    DesktopAdapter -->|Command DTO| Atlas
    
    Atlas -.->|Result DTO| CLI
    Atlas -.->|ResponseEnvelope| IDEAdapter
```

Since Phase 15, every adapter above negotiates a `PlatformCapabilityManifest` via `negotiate(atlas)` and presents an `AdapterContext` identity, structurally satisfying `atlas.adapters.protocol.PlatformAdapter`. Only the CLI (in-process) uses named Command DTOs directly; out-of-process/protocol adapters use `Atlas.handle(RequestEnvelope)`. See [Platform Request Dispatch Diagram](platform-request-dispatch.md).
