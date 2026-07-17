# Intelligence Layer Boundary Diagram

This diagram shows the stateless AI boundaries and context aggregation layers, illustrating that the AI Orchestration layer only reads data and cannot directly write to subsystem repositories. State changes must flow through the human review gate and commit services.

```mermaid
graph TD
    classDef safety fill:#ffd,stroke:#f66,stroke-width:2px;
    classDef database fill:#9f9,stroke:#333,stroke-width:2px;

    subgraph User Space
        User[Human Developer]
    end

    subgraph Stateful Domain Layer
        Repo[Subsystem Repositories]:::database
        DomainServ[Subsystem Domain Services]
    end

    subgraph Prompt Management
        Registry[Prompt Registry]
        Prompt[Prompt Template]
    end

    subgraph Multi-Protocol AI Runtime
        CA[Context Assembler Service]
        Executor[Prompt Executor]
        Provider[Protocol Adapter]
        Model[External Model Endpoint]
    end

    User -->|Triggers| WO[Workflow Orchestration]
    WO -->|Requests context| CA
    CA -->|Reads Approved Snapshots| Repo
    CA -->|Compiles| Context[ContextPayload]:::safety
    WO -->|Invokes| Executor
    Executor -->|Resolves Template| Registry
    Registry --> Prompt
    Executor -->|Injects Context & Template| Prompt
    Executor -->|Submits stateless AIRequest| Provider
    Provider -->|Queries API| Model
    Model -->|Returns JSON| Provider
    Provider -->|Translates to AIResponse| Executor
    Executor -->|Returns typed draft| WO
    
    WO -->|Review Gate| User
    
    User -->|Approves Commit| WO
    WO -->|Trigger Mutation Flow| CommServ[Proposal Commit Service]
    CommServ -->|Runs Validator| DomainServ
    CommServ -->|Writes state| Repo
```
