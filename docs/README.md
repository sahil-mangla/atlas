# ATLAS Architecture Documentation (v1.0 Baseline, Phase 13–15)

Welcome to the official ATLAS Architecture Baseline documentation. This reference captures the canonical architecture and design patterns of the ATLAS platform after the completion and stabilization of Phase 1–13, the Phase 14 Presentation Layer, and the Phase 15 Platform Layer.

---

## Documentation Structure

### 1. [Glossary](glossary.md)
Canonical definitions of terminology matching the codebase.

### 1a. [FAQ](faq.md)
Q&A walkthrough of the architecture, workflow, AI constitution, and knowledge lifecycle — a faster entry point than reading every doc below.

### 1b. [Observability Guide](observability.md)
Request traces, AI usage capture, exporters, configuration, and operational behavior.

### 1c. [Evaluation and Regression Guide](evaluations.md)
YAML benchmark tasks, real-provider runs, reports, and baseline comparison.

### 1d. [Semantic Knowledge Retrieval](semantic-retrieval.md)
Optional relevance ranking of published knowledge with an embedded vector index, and its evaluation.

### 1e. [Market and Competitor Research](market-research.md)
Searching GitHub, Hacker News and (with a key) the web for existing products, so research names alternatives and gaps.

### 1f. [Testing Without an AI Provider](testing.md)
The offline `SCRIPTED` protocol, the test layers, and how CI runs with no keys.

### 2. Architecture Reference
- **[Application Platform Layer](architecture/application-platform.md)**: The public Atlas SDK boundary, commands, results, and exception contract.
- **[Client Adapter Layer](architecture/client-adapters.md)**: Presentation and transport bindings exposing the Atlas SDK to external execution environments.
- **[CLI Usage Guide](usage/cli.md)**: Usage documentation for the ATLAS CLI client adapter.
- **[Package Map](architecture/package-map.md)**: What each package under `atlas_eng/` is responsible for.
- **[Architecture Principles](architecture/architecture-principles.md)**: Core design values (e.g. Domain First, Dependency Inversion, Immutability).
- **[System Overview](architecture/system-overview.md)**: Product vision and the 11 major subsystems' boundaries and responsibilities.
- **[Layered Architecture](architecture/layered-architecture.md)**: Vertical execution flows and commit mutations across layers.
- **[Engineering Workflow](architecture/engineering-workflow.md)**: Lifecycles, objectives, and transition state machine rules.
- **[Workflow Stage Execution](architecture/workflow-stages.md)**: AI-assisted and human-driven stage responsibilities.
- **[Intelligence Layer](architecture/intelligence-layer.md)**: Coordination of AI integration services under constitutional safety boundaries.
- **[Engineering Knowledge Layer](architecture/engineering-knowledge-layer.md)**: Phase 13 knowledge boundaries, lifecycle, retrieval, and persistence.
- **[Multi-Protocol AI Runtime](architecture/multi-protocol-ai-runtime.md)**: Protocol factory, protocol adapters, and protocol-independent prompt execution.
- **[Domain Model](architecture/domain-model.md)**: The lightweight Project aggregate root and sub-aggregate boundaries.
- **[Persistence Architecture](architecture/persistence.md)**: Filesystem storage details, path resolution inversion, and compensating transaction rollbacks.
- **[Traceability](architecture/traceability.md)**: Immutable provenance chains connecting evidence down to commits.
- **[Engineering Constitution](architecture/engineering-constitution.md)**: Coding quality rules and review compliance policies.
- **[AI Constitution](architecture/ai-constitution.md)**: Core rules (e.g. statelessness, no direct mutations, schema checks) governing AI generation safety.
- **[Subsystem Extension Guide](architecture/extension-guide.md)**: Walkthrough for adding a new engineering lifecycle stage.
- **[Presentation Layer (Phase 14)](architecture/presentation-layer.md)**: The upper, non-engine layer composing typed immutable Views from the Atlas read-model API and rendering them to JSON/Markdown/CLI.
- **[Presentation Extension Guide](guides/presentation-extension-guide.md)**: Walkthrough for adding a new View kind to the presentation layer.
- **[Platform Layer (Phase 15)](architecture/platform-layer.md)**: The Capability Layer, Contract Layer, and Adapter Boundary formalizing the single doorway every client goes through before reaching an engine subsystem.
- **[Observability Guide](observability.md)**: Request-boundary tracing, AI token usage, JSONL export, and failure behavior.
- **[Evaluation and Regression Guide](evaluations.md)**: The benchmark task format, runner commands, reports, and baselines.

### 3. Architecture Decisions (ADRs)
- **[ADR-001: Architecture Baseline v1.0](decisions/adr-001-architecture-baseline-v1.md)**: Initial ADR locking the v1.0 design baseline.
- **[ADR-002: Application Platform Layer](decisions/adr-002-application-platform-layer.md)**: Canonical public SDK and composition-root decision.
- **[ADR-003: Engineering Knowledge Layer](decisions/adr-003-engineering-knowledge-layer.md)**: Phase 13 knowledge boundaries, review, and immutability rules.
- **[ADR-004: Platform Capability & Contract Layer](decisions/adr-004-platform-capability-contract-layer.md)**: Phase 15 Capability Layer, Contract Layer, and Adapter Boundary decision.

### 4. Architecture Diagrams
- **[Application Platform Layer](diagrams/application-platform.md)**
- **[Client Adapter Layer](diagrams/client-adapter-layer.md)**
- **[Subsystem Interactions](diagrams/system-overview.md)**
- **[Engineering Pipeline](diagrams/engineering-pipeline.md)**
- **[Proposal Lifecycle](diagrams/proposal-lifecycle.md)**
- **[Intelligence Layer Boundary](diagrams/intelligence-layer.md)**
- **[Repository & Rollback Flow](diagrams/repository-flow.md)**
- **[Domain & Traceability Links](diagrams/domain-relations.md)**
- **[Runtime Request Lifecycle](diagrams/request-lifecycle.md)**
- **[Multi-Protocol AI Runtime](diagrams/multi-protocol-ai-runtime.md)**
- **[Knowledge Lifecycle](diagrams/knowledge-lifecycle.md)**
- **[Knowledge Workflow Integration](diagrams/knowledge-workflow-integration.md)**
- **[Presentation Flow (Phase 14)](diagrams/presentation-flow.md)**: Atlas Facade to PlatformOrchestrationService to Collectors to Read Models to Views to Renderers to RenderResult.
- **[Platform Request Dispatch (Phase 15)](diagrams/platform-request-dispatch.md)**: `Atlas.handle(RequestEnvelope)` through Capability dispatch to `ResponseEnvelope`.
- **[Observed Platform Request](diagrams/observed-platform-request.md)**: Request instrumentation, shared AI usage capture, and trace export around the platform boundary.

### 5. Project History
- **[History](history/README.md)**: The original blueprint, phase plans, sprint reports and progress log, kept for reference. They describe the code as it was when written.
