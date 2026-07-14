# Repository Dependency Inversion and Rollback Flow Diagram

This diagram illustrates how concrete repositories depend on abstract contracts, resolve their paths dynamically through `ProjectRepository`, and coordinate with the compensating unit of work rollback transaction.

```mermaid
graph TD
    classDef contract fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef concrete fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;

    subgraph Abstractions
        ProjectRepo[ProjectRepository]:::contract
        ArchRepo[ArchitectureRepository]:::contract
        PlanRepo[PlanningRepository]:::contract
        ResRepo[ResearchRepository]:::contract
    end

    subgraph Concrete Implementations
        FS_ProjectRepo[FilesystemProjectRepository]:::concrete
        FS_ArchRepo[FilesystemArchitectureRepository]:::concrete
        FS_PlanRepo[FilesystemPlanningRepository]:::concrete
        FS_ResRepo[FilesystemResearchRepository]:::concrete
    end

    FS_ProjectRepo -.->|Implements| ProjectRepo
    FS_ArchRepo -.->|Implements| ArchRepo
    FS_PlanRepo -.->|Implements| PlanRepo
    FS_ResRepo -.->|Implements| ResRepo

    FS_ArchRepo -->|Resolves path| ProjectRepo
    FS_PlanRepo -->|Resolves path| ProjectRepo
    FS_ResRepo -->|Resolves path| ProjectRepo

    subgraph Transaction Boundary
        UOW[ProposalCommitUnitOfWork]
        UOW -->|Captures backups & restores / deletes| FS_ArchRepo
        UOW -->|Captures backups & restores / deletes| FS_PlanRepo
        UOW -->|Captures backups & restores / deletes| FS_ResRepo
    end
```
