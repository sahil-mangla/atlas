# ATLAS Glossary

This glossary defines the canonical engineering and domain terminology used throughout the ATLAS platform. These definitions correspond to the Pydantic domain models in `engine/domain/` and orchestrations in `engine/workflow/` and `engine/ai/`.

---

### Project
The top-level aggregate root representing the engineering system context. It holds metadata, status, current workflow stage, and references to other sub-aggregates by ID to remain lightweight and decoupled.

### Client Adapter
An external interface (e.g., CLI, Desktop, Web, IDE Extension, MCP Server) that interacts with ATLAS. Clients are not part of the engine; they sit above the Application Platform Layer and initiate actions using Commands.

### Atlas Facade
The canonical public API (`atlas/_service.py`) for the ATLAS platform. It encapsulates internal engine complexity and presents a unified `Atlas` class to all Client Adapters.

### Command DTO
An immutable, serializable, transport-independent Data Transfer Object that encapsulates a requested action from a Client Adapter (e.g., `ExecuteStageCommand`).

### Result DTO
A pure data structure returned by the Atlas Facade. Results do not expose internal domain entities, repository references, or engine implementations.

### Artifact
Any versioned file, model, or metadata structure created or managed within the project workspace. Examples include design specifications, code files, and snapshot files.

### Snapshot
An immutable, versioned freeze of a subsystem's domain state. Snapshots (e.g., `ResearchSnapshot`, `PlanningSnapshot`, `ArchitectureSnapshot`, `EvaluationSnapshot`) are created, verified, and committed to disk, serving as the historical record and context baseline.

### Proposal
A stateless, generated draft of suggested domain changes (e.g., `ResearchProposalDraft`, `PlanningProposalDraft`), encapsulated in an `AIProposal` container. A proposal remains a draft until a human review approves it.

### Aggregate
A cluster of associated domain objects treated as a single transaction unit. In ATLAS, `Project` is the root aggregate, containing sub-aggregates (Research, Planning, Architecture, Workflow, Memory, Evaluation) linked by unique IDs.

### ADR (Architectural Decision Record)
A formal document within the Architecture subsystem capturing a critical design decision, including its unique status, context, description, and architectural consequences.

### Evidence
A raw technical fact, external source reference, or literature summary gathered in the Research stage (`Evidence` / `ResearchSource`).

### Finding
A synthesized insight or domain fact derived from one or more pieces of evidence (`ResearchFinding` or `EvaluationFinding`).

### Opportunity
A potential engineering path, design alternative, or feature candidate supported by research findings (`Opportunity`).

### Constraint
A mandatory technical, business, or operational limit that system designs and code modifications must respect (`Constraint` or `ArchitectureConstraint`).

### Assumption
A technical premise or hypothesis accepted during design that carries some level of risk (`Assumption` or `ArchitectureAssumption`).

### Workflow
The state machine driving the project through sequential engineering stages, tracking current status, completed stages, and pending objectives.

### Context
A frozen, immutable package of subsystem states (`ContextPayload`) containing snapshot references and serialized context dumps passed to the AI provider.

### Memory Candidate
Conversations, system variables, or tool outputs analyzed for long-term project knowledge retention (`MemoryCandidate` / `MemoryEntry`).

### Engineering Review
A formal audit evaluating code modifications or design proposals for correctness, security, and conformance.

### Traceability
The immutable lineage linking upstream requirements and research findings down to architectural designs, task roadmaps, and final commits (`TraceabilityLink`).

### Readiness
The evaluation status (`ReadinessReview`) verifying that all active objectives for the current workflow stage have been completed before a transition can occur.

### KnowledgeCandidate
A proposed unit of engineering knowledge (principle, pattern, standard, constraint, or lesson learned) extracted from approved snapshots or submitted by a human, pending human review and approval.

### PublishedKnowledge
An approved, versioned, immutable engineering knowledge entry active in the project context. It is frozen and content cannot be mutated.

### KnowledgeActor
A value object representing the identity and type (human, AI, workflow, system, import) of the actor associated with a knowledge action.

### KnowledgeProvenance
The metadata tracing the origin of a knowledge entry (e.g. the source snapshot type, ID, extraction time, and extracting actor).

### Deduplication Fingerprint
A deterministic SHA-256 hash computed from normalized title, content, category, and tags to identify and block exact duplicates during candidate submission.

### Presentation Layer
The Phase 14 `presentation/` package: an upper, non-engine layer that composes typed, immutable Views from the Atlas facade's read-model API and renders them to concrete output formats. See [Presentation Layer Architecture](architecture/presentation-layer.md).

### Atlas Read Model
An immutable, frozen Pydantic DTO (`presentation/read_models/models.py`) returned by an `Atlas.get_*_read_model` method, sourced from existing Phase 1-13 services and never exposing engine entities or repositories. The sole data source for presentation Collectors.

### Collector (Presentation)
A Phase 14 class (`presentation/collectors/collectors.py`) that calls one or more Atlas read-model methods and aggregates the results into a single immutable View. Collectors own presentation aggregation and derived values; they never render, call repositories, call engine services directly, perform AI work, or mutate engineering state.

### View (Presentation)
A deeply immutable, frozen Pydantic model (`presentation/views/models.py`) composed from Components, representing a fully computed, ephemeral, renderer-independent presentation surface (e.g. `ProjectDashboardView`). Views contain no business logic and no engine models.

### Component (Presentation)
An immutable leaf presentation object (`StatusBadge`, `Metric`, `Section` in `presentation/components/models.py`) with no rendering logic, no Atlas dependency, and no business logic. Views assemble Components; Components never assemble Views.

### PlatformOrchestrationService
The Phase 14 orchestration service (`presentation/orchestration/platform.py`) that selects a Collector and delegates to it. It receives all Collectors via constructor injection and never constructs them itself; it contains no business rules, does not render, and owns no persistence or repositories.

### Renderer
A Phase 14 class (`presentation/renderers/base.py`) implementing the `Renderer` protocol that formats an immutable View into a `RenderResult` for one output format (JSON, Markdown, or CLI text). Renderers perform formatting only -- they never call Atlas, never compute business meaning, and never mutate their input view.

### RenderResult
The frozen dataclass (`presentation/renderers/result.py`) returned by every Renderer, carrying rendered `content`, `media_type`, `renderer` identity, and an immutable (`MappingProxyType`) `metadata` mapping.
