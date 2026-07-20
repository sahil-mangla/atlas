# Application Platform Diagram

```mermaid
flowchart TD
    subgraph Clients["First and Third Party Clients"]
        CLI["CLI Adapter"]
        VSCode["VS Code Extension"]
        Web["Web Interface"]
        MCP["MCP Server Adapter"]
    end

    subgraph AtlasSDK["Application Platform Layer (Atlas SDK)"]
        AtlasFacade["Atlas Facade (atlas/_service.py)"]
        Commands["Commands DTOs"]
        Results["Results DTOs"]
        Exceptions["Public Exceptions"]
        Handle["Atlas.handle() (Phase 15, preferred for MCP/REST/IDE/AI)"]
        Capabilities["Capability Layer (atlas/capabilities/)"]
        Handle --> Capabilities
        AtlasFacade --> Capabilities
    end

    subgraph Engine["Engine (Hidden Internal Implementation)"]
        Project["Project Subsystem"]
        Workflow["Workflow Subsystem"]
        Orchestration["Workflow Orchestration"]
        AI["AI Services"]
        Domain["Domain Entities"]
    end

    CLI -->|ExecuteCommand| AtlasFacade
    VSCode -->|GetWorkflowStatus| AtlasFacade
    Web -->|CreateProject| AtlasFacade
    MCP -->|ProposeChanges| AtlasFacade

    AtlasFacade -->|Translates to domain calls| Project
    AtlasFacade -->|Reads state| Workflow
    AtlasFacade -->|Drives generation| Orchestration
    
    Orchestration --> AI
    Project --> Domain
    Workflow --> Domain

    style AtlasSDK fill:#f9f,stroke:#333,stroke-width:2px
    style Engine fill:#eef,stroke:#333,stroke-dasharray: 5 5
```

See [Platform Request Dispatch Diagram](platform-request-dispatch.md) for the full Phase 15 dispatch flow, including the envelope path and the five-capability breakdown.
