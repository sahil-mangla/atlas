# Presentation Flow Diagram (Phase 14)

```mermaid
flowchart TD
    subgraph Clients["Platform / Clients"]
        Caller["Any Atlas caller"]
    end

    subgraph AtlasFacade["Atlas Facade (atlas/_service.py)"]
        ReadModelAPI["get_*_read_model(project_id)"]
        ViewAPI["get_*_view(project_id)"]
        RenderAPI["render(view, renderer, contract)"]
    end

    subgraph Orchestration["PlatformOrchestrationService"]
        Orch["Selects collector, delegates"]
    end

    subgraph Collectors["Collectors"]
        PDC["ProjectDashboardCollector"]
        WSC["WorkflowStatusCollector"]
        RSC["ResearchSummaryCollector"]
        KSC["KnowledgeSummaryCollector"]
        DC["DiagnosticsCollector"]
    end

    subgraph ReadModels["Typed Atlas Read Models"]
        PRM["ProjectReadModel"]
        WRM["WorkflowReadModel"]
        RRM["ResearchReadModel"]
        KRM["KnowledgeReadModel"]
        DRM["DiagnosticsReadModel"]
    end

    subgraph Engine["Phase 1-13 Services (engine/*)"]
        ProjectSvc["Project services"]
        WorkflowSvc["Workflow repo + readiness service"]
        ResearchSvc["Research repository"]
        KnowledgeSvc["Knowledge repository"]
    end

    subgraph Views["Immutable Views"]
        View["ProjectDashboardView / WorkflowStatusView / ... (frozen, tuple-based)"]
    end

    subgraph Renderers["Renderers"]
        Json["JsonRenderer"]
        Md["MarkdownRenderer"]
        Cli["CliRenderer"]
    end

    Result["RenderResult (frozen, immutable metadata)"]

    Caller -->|"get_project_dashboard_view(id)"| ViewAPI
    ViewAPI --> Orch
    Orch --> PDC
    Orch --> WSC
    Orch --> RSC
    Orch --> KSC
    Orch --> DC

    PDC -->|"atlas.get_project_read_model"| ReadModelAPI
    PDC -->|"atlas.get_workflow_read_model"| ReadModelAPI
    PDC -->|"atlas.get_research_read_model"| ReadModelAPI
    PDC -->|"atlas.get_knowledge_read_model"| ReadModelAPI

    ReadModelAPI --> PRM
    ReadModelAPI --> WRM
    ReadModelAPI --> RRM
    ReadModelAPI --> KRM
    ReadModelAPI --> DRM

    PRM --> ProjectSvc
    WRM --> WorkflowSvc
    RRM --> ResearchSvc
    KRM --> KnowledgeSvc

    PDC --> View
    WSC --> View
    RSC --> View
    KSC --> View
    DC --> View

    View -->|"atlas.render(view, renderer)"| RenderAPI
    RenderAPI --> Json
    RenderAPI --> Md
    RenderAPI --> Cli
    Json --> Result
    Md --> Result
    Cli --> Result
    Result --> Caller

    style AtlasFacade fill:#f9f,stroke:#333,stroke-width:2px
    style Engine fill:#eef,stroke:#333,stroke-dasharray: 5 5
    style Views fill:#efe,stroke:#333
```

## Reading This Diagram

- **Rendering is a separate step from view retrieval.** A caller may fetch `get_project_dashboard_view` and never call `render` at all (e.g. to inspect the immutable view directly, as tests do).
- **Collectors are the only presentation code that talks to Atlas**, and only through the five `get_*_read_model` methods -- never through repositories, engine services, or the filesystem directly.
- **`Engine (Phase 1-13 Services)` is only reachable from inside the Atlas Facade box.** Nothing in `Collectors`, `Views`, or `Renderers` has an edge into it; this mirrors the static import-boundary guarantee enforced by `tests/architecture/test_presentation_boundaries.py`.
- **Views feed both `render` and callers directly** -- rendering is optional and always operates on the same immutable object a caller could inspect without rendering.

See [Presentation Layer Architecture](../architecture/presentation-layer.md) for the full write-up and [Presentation Extension Guide](../guides/presentation-extension-guide.md) for how to add a new view kind.
