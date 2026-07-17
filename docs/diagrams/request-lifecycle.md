# Runtime Request Lifecycle Diagram

This diagram represents the step-by-step runtime request lifecycle of the ATLAS platform, detailing the flow from user action trigger, through generation, human review, commit processing, verification, and stage transition.

```mermaid
graph TD
    classDef step fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef gate fill:#ffe0b2,stroke:#fb8c00,stroke-width:2px;

    User([User]) -->|1. Triggers generate_proposal| WO[Workflow Orchestrator]:::step
    WO -->|2. Identifies stage executor| SE[Stage Executor]:::step
    SE -->|3. Requests proposal draft| AES[AI Engineering Service]:::step
    AES -->|4. Assembles context & builds request| AO[AI Orchestration]:::step
    AO -->|5. Invokes PromptExecutor| PE[Prompt Executor]:::step
    PE -->|6. Invokes protocol adapter| AP[AIProvider / Protocol Adapter]:::step
    AP -->|7. Emits generated draft| Prop[Proposal]:::step
    Prop -->|8. Evaluated by human| HR[Human Review]:::gate
    
    HR -->|Approved| PC[Proposal Commit]:::step
    HR -->|Rejected| WO
    
    PC -->|9. Mutates state| DS[Domain Services]:::step
    DS -->|10. Persists JSON files| Repos[Repositories]:::step
    Repos -->|11. Evaluates objectives checklist| WR[Workflow Readiness]:::gate
    WR -->|12. Transitions stage| WT[Workflow Transition]:::step
```
