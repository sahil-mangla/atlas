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
