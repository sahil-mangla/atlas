<!-- refreshed: 2026-07-19 -->
# Architecture

**Analysis Date:** 2026-07-19

## System Overview

```text
┌──────────────────────────────────────────────────────────────────┐
│                    Client Adapters (Top Layer)                   │
├─────────────────┬──────────────┬────────────┬────────┬───────────┤
│   CLI Client    │ REST Client  │ MCP Client │ IDE    │  Desktop  │
│ `clients/cli`   │`clients/rest`│`clients/mcp│`client`│`clients/  │
│                 │              │     `      │ `      │ desktop`  │
└────────┬────────┴──────┬───────┴────┬───────┴────┬───┴───────────┘
         │               │            │            │
         └───────────────┼────────────┼────────────┘
                         │            │
        ┌────────────────▼────────────▼─────────────┐
        │  Presentation Layer (Orchestration)       │
        │  `presentation/orchestration/`            │
        │  - Collectors, Renderers, Views           │
        └───────────────────┬──────────────────────┘
                            │
        ┌───────────────────▼──────────────────────┐
        │   Application Platform Layer (Atlas)     │
        │   `atlas/_service.py` — Public Façade    │
        │   Command DTO dispatch, result mapping   │
        │   - create_project()                     │
        │   - load_project()                       │
        │   - get_workflow_status()                │
        │   - execute_stage()                      │
        │   - approve/reject proposals             │
        └───────────────────┬──────────────────────┘
                            │
        ┌───────────────────▼──────────────────────────────────────┐
        │         Engine Subsystems Layer                          │
        ├────────────────────────────────────────────────────────  │
        │  Workflow Orchestration  (engine/workflow/)              │
        │  ├─ StageExecutor<T>: [Research | Planning |            │
        │  │   Architecture | Evaluation]                          │
        │  ├─ WorkflowOrchestrationService                         │
        │  └─ WorkflowReadinessService                             │
        │                                                          │
        │  Project Subsystem  (engine/project/)                    │
        │  ├─ ProjectCreationService                               │
        │  ├─ ProjectLoadingService                                │
        │  ├─ ProjectRegistryService                               │
        │  └─ ProjectLifecycleService                              │
        │                                                          │
        │  Research (engine/research/) ──┐                         │
        │  Planning (engine/planning/)   │                         │
        │  Architecture (engine/architecture/) ├─ AI Engineering   │
        │  Evaluation (engine/evaluation/)  │   │ Services Layer   │
        │                                ─┤   (engine/ai/)        │
        │  Knowledge (engine/knowledge/)   │   │                   │
        │  Memory (engine/memory/)       ─┘   └─ AI Services,     │
        │                                      Orchestration,     │
        │  PromptLoader (engine/prompt/)       Transformers       │
        │                                                          │
        └─────────────────────┬──────────────────────────────────┘
                              │
        ┌─────────────────────▼──────────────────────┐
        │   Domain Models Layer                      │
        │   `engine/domain/*.py`                     │
        │   - Strongly-typed Pydantic models         │
        │   - Project, Workflow, Research, Planning, │
        │   - Architecture, Evaluation, Memory, etc. │
        └─────────────────────┬──────────────────────┘
                              │
        ┌─────────────────────▼──────────────────────┐
        │   Repository Layer (Persistence)          │
        │   `engine/*/fs_repository.py`              │
        │   - FilesystemProjectRepository            │
        │   - FilesystemWorkflowRepository           │
        │   - FilesystemResearchRepository           │
        │   - FilesystemPlanningRepository           │
        │   - FilesystemArchitectureRepository       │
        │   - FilesystemEvaluationRepository         │
        │   - FilesystemKnowledgeRepository          │
        │   - FilesystemMemoryRepository             │
        └─────────────────────┬──────────────────────┘
                              │
        ┌─────────────────────▼──────────────────────┐
        │   External Dependencies                    │
        │   - Google Generative AI Provider          │
        │   - Filesystem storage (.atlas/)           │
        │   - Pydantic settings                      │
        └────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **Atlas** | Public platform facade; command dispatch to engine services | `atlas/_service.py` |
| **Project Subsystem** | Project lifecycle (create, load, archive, list) | `engine/project/services.py` |
| **Workflow Orchestration** | Stage transitions, readiness evaluation, proposal generation | `engine/workflow/orchestration.py` |
| **Research Subsystem** | Problem definition, evidence collection, finding synthesis | `engine/research/services.py` |
| **Planning Subsystem** | Scope, milestone, epic, task decomposition | `engine/planning/services.py` |
| **Architecture Subsystem** | Component design, ADR, interface contracts, risk analysis | `engine/architecture/services.py` |
| **Evaluation Subsystem** | Readiness assessment, quality validation, finding generation | `engine/evaluation/services.py` |
| **Knowledge Subsystem** | Knowledge deduplication, approval workflow, retrieval | `engine/knowledge/services.py` |
| **Memory Subsystem** | Dialogue history, context assembly | `engine/memory/fs_repository.py` |
| **AI Integration** | Prompt execution, proposal generation, transformers, validators | `engine/ai/engineering_services.py` |
| **CLI Adapter** | Command parsing, dispatch via Atlas SDK, result rendering | `clients/cli/application.py` |

## Pattern Overview

**Overall:** Multi-layered hexagonal architecture with command/result DTO boundary at application layer, stateless AI-driven stage executors, and filesystem-based persistence.

**Key Characteristics:**
- **Clean boundaries:** Public SDK (`atlas/`) only exports DTOs and facade; engine packages never leaked to clients
- **Subsystem autonomy:** Each subsystem (research, planning, architecture, etc.) manages own domain models and lifecycle
- **Proposal-driven workflow:** AI generates proposals, humans approve/reject; commit service transforms into persisted domain models
- **Type safety:** Pydantic models with strict validation throughout; generic `AIProposal[T]` for typed proposal containers
- **Single project root:** Project aggregate root with references to owned sub-aggregates by ID (not embedding full state)

## Layers

**Presentation Layer (Clients & Renderers):**
- Purpose: Translate external execution contexts (CLI, REST, MCP, IDE, Desktop) to/from Atlas SDK DTOs
- Location: `clients/`, `presentation/`
- Contains: Command parsing, result rendering, context collection
- Depends on: `atlas/` (DTOs, exceptions) only; never imports `engine/`
- Used by: End-user invocations (CLI, web, IDE extensions)

**Application Platform Layer (Atlas Façade):**
- Purpose: Public API boundary; command dispatch and exception mapping
- Location: `atlas/_service.py`, `atlas/commands.py`, `atlas/results.py`
- Contains: `Atlas` facade, command DTOs, result DTOs, application exceptions
- Depends on: Engine services injected at bootstrap; exception mapping
- Used by: Client adapters exclusively

**Bootstrap/Composition Root:**
- Purpose: Wire all engine subsystems and AI components; return configured façade
- Location: `atlas/_bootstrap.py`
- Contains: Dependency injection, service instantiation, registry construction

**Engine Subsystems:**
- Purpose: Domain-driven business logic per problem area
- Location: `engine/{research,planning,architecture,evaluation,workflow,project,knowledge,memory,ai}/`
- Pattern: Each subsystem is independently deployable and testable
  - `services.py`: Business logic operations
  - `fs_repository.py`: Persistence abstraction
  - Domain models embedded in `engine/domain/`
  - Exceptions in `exceptions.py`

**Domain Layer:**
- Purpose: Strongly-typed ubiquitous language via Pydantic
- Location: `engine/domain/*.py`
- Contains: `Project`, `Workflow`, `Research`, `Planning`, `Architecture`, `Evaluation`, `Memory`, `AIProposal`, etc.
- All models are Pydantic BaseModel with exhaustive field documentation

**Persistence/Repository Layer:**
- Purpose: Abstract filesystem-based storage
- Location: `engine/*/fs_repository.py` (all subsystems)
- Pattern: Repository interface in `engine/*/repository.py`, filesystem implementation in `fs_repository.py`
- Storage: `.atlas/` directory in project root with JSON/YAML serialized aggregates

## Data Flow

### Primary Request Path: Execute Stage

1. **Client invocation** (`clients/cli/application.py:main()`)
   - Parse command-line arguments → `ExecuteStageCommand` DTO

2. **Command dispatch** (`atlas/_service.py:execute_stage()`)
   - Validate command, retrieve project, check workflow readiness

3. **Stage execution** (`engine/workflow/orchestration.py:WorkflowOrchestrationService`)
   - Retrieve appropriate StageExecutor by workflow stage
   - Call executor.generate_proposal() with context

4. **AI proposal generation** (per-stage, e.g., `ResearchStageExecutor` → `ResearchAIEngineeringService`)
   - Context assembly from prior stages' snapshots (`engine/ai/services.py:ContextAssemblerService`)
   - Prompt loading and execution (`engine/ai/executor.py:PromptExecutor`)
   - AI provider call (Google Generative AI)
   - Proposal validation (e.g., `ResearchProposalValidator`)
   - Return typed `AIProposal[ResearchProposalDraft]`

5. **Proposal pending** (`atlas/_service.py` stores in-memory cache)
   - Keyed by `(project_id, proposal_id)` for later approval/rejection

6. **Human review** (`atlas/_service.py:approve_proposal()` or `reject_proposal()`)
   - If approved: commit service transforms proposal to domain models
   - If rejected: proposal discarded; workflow remains unchanged

7. **Commit & transition** (`engine/ai/engineering_services.py:ProposalCommitService`)
   - Transformers (e.g., `ResearchProposalTransformer`) write to repositories
   - Workflow readiness updated with snapshots
   - Transition available for next stage

### Secondary Flow: Knowledge Candidate Review

1. **Knowledge extraction** (per-stage via `engine/knowledge/extractors/`)
   - Extractors (e.g., `ResearchKnowledgeExtractor`) scan completed stages for learnings
   - Populate `KnowledgeCandidates` and queue for human review

2. **Candidate approval** (`atlas/_service.py:review_knowledge_candidate()`)
   - Approved candidates move to `PublishedKnowledge` (project-scoped)

**State Management:**
- Workflow state: Immutable history log (append-only) in `Workflow.history`
- Completed stages: Append-only in `Workflow.completed_stages`
- Proposals: In-memory only until approved (then committed to repositories)
- Context: Assembled on-demand from stage snapshots in repositories

## Key Abstractions

**`StageExecutor[T]`:**
- Purpose: Encapsulate proposal generation for a specific workflow stage
- Examples: `ResearchStageExecutor`, `PlanningStageExecutor`, `ArchitectureStageExecutor`
- Pattern: Generic over proposal draft type; all delegate to corresponding AI Engineering Service

**`AIProposal[T]`:**
- Purpose: Typed container for AI-generated proposals with metadata
- Fields: proposal ID, type, status, content (of type T), generation timestamp, confidence
- Used by: All stage executors to return proposals; façade caches pending proposals by ID

**`ContextPayload` and `ContextAssemblerService`:**
- Purpose: Assemble prior-stage snapshots into LLM context window
- Location: `engine/ai/context.py`, `engine/ai/services.py`
- Pattern: Stateless assembly; consumed by PromptExecutor

**`ProposalTransformer` family:**
- Purpose: Hydrate AI proposal drafts into full domain models post-approval
- Examples: `ResearchProposalTransformer`, `PlanningProposalTransformer`, `ArchitectureProposalTransformer`
- Pattern: Each transformer composes the subsystem services needed to write related artifacts

**`Repository` abstraction:**
- Purpose: Decouple domain logic from storage implementation
- Interface: Get, save, list, delete by project_id or ID
- Implementation: FilesystemRepository stores to `.atlas/{project_id}/{subsystem}/` in JSON

## Entry Points

**CLI Entry Point:**
- Location: `clients/cli/application.py:main()`
- Triggers: User invocation of `atlas` CLI command
- Responsibilities: Parse argv, create CLIApplication, dispatch commands, render results

**Programmatic Entry Point:**
- Location: `atlas.create()`
- Triggers: Any client calling `atlas.create()` (CLI, testing, future SDKs)
- Responsibilities: Bootstrap platform, return configured Atlas facade

**Stage Execution Entry:**
- Location: `atlas._service.py:execute_stage()`
- Triggers: User calls `atlas execute-stage <stage>`
- Responsibilities: Validate readiness, invoke workflow orchestration, cache proposal

## Architectural Constraints

- **Threading:** Single-threaded Python; no async/await yet. All I/O is synchronous (filesystem, AI provider).
- **Global state:** No module-level singletons; all services injected at bootstrap via `_bootstrap.py`. Proposal cache is instance-scoped to Atlas facade.
- **Circular imports:** Domain models (`engine/domain/`) import only Pydantic and enums; never import services.
- **Repository scope:** Each repository is keyed by `project_id`; multi-project support built-in via project registry.
- **AI provider:** Pluggable via `engine/ai/factory.py:ProtocolFactory`; currently Google Generative AI; extensible for Anthropic, OpenAI, etc.
- **Serialization:** Pydantic JSON serialization; custom serializers in `engine/*/serializers.py` for complex types (dates, UUIDs).

## Anti-Patterns

### Direct Engine Imports in Clients

**What happens:** Client code imports `engine.domain.*` or `engine.services.*` directly

**Why it's wrong:** Breaks clean architectural boundary; tightly couples clients to engine; makes engine internals public

**Do this instead:** Import only from `atlas/` in client code. Use DTOs from `atlas.commands` and `atlas.results`. Example:
```python
# WRONG:
from engine.domain.project import Project

# RIGHT:
from atlas.commands import CreateProjectCommand
from atlas.results import ProjectResult
```

### Mutable Domain State in Services

**What happens:** Services mutate domain model in-place, then save to repository

**Why it's wrong:** Harder to reason about state; difficult to implement validation or transaction semantics

**Do this instead:** Services construct new domain models or call builder methods, then save. Research already follows this: `research = Research(...); repository.save(research)`.

### Embedding Full Aggregates in References

**What happens:** Project stores the full Workflow object instead of just `workflow_id`

**Why it's wrong:** Duplication; two sources of truth; stale data; circular coupling

**Do this instead:** Project references Workflow by ID only: `workflow_id: UUID | None`. Load via `workflow_repo.get_by_project_id(project_id)` when needed.

## Error Handling

**Strategy:** Domain-specific exceptions at engine layer; mapped to application exceptions at façade boundary.

**Patterns:**
- Engine exceptions inherit from subsystem base (e.g., `ProjectException`, `WorkflowException`) in `engine/{subsystem}/exceptions.py`
- Façade catches engine exceptions and maps to application exceptions (e.g., `ProjectNotFoundException` → `atlas.exceptions.ProjectNotFoundError`)
- Client adapters catch only `atlas.exceptions.ApplicationError` and render error messages
- Example flow: `engine/project/exceptions.py:ProjectNotFoundException` → `atlas/_service.py` maps to `atlas/exceptions.py:ProjectNotFoundError` → client renders

## Cross-Cutting Concerns

**Logging:** No structured logging framework yet; uses `print()`. Future: migrate to Python `logging` module with level configuration.

**Validation:** Pydantic handles most; custom validators in domain models. Example: `Workflow` validates forward-only transitions.

**Authentication:** Not yet implemented; future phases will add user context and permission checks.

---

*Architecture analysis: 2026-07-19*
