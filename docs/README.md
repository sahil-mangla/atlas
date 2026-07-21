# ATLAS Architecture Documentation (v1.0 Baseline, Phase 13–15)

Welcome to the official ATLAS Architecture Baseline documentation. This reference captures the canonical architecture and design patterns of the ATLAS platform after the completion and stabilization of Phase 1–13, the Phase 14 Presentation Layer, and the Phase 15 Platform Layer.

---

## Documentation Structure

### 1. [Glossary](file:///Users/sahilmangla/atlas/docs/glossary.md)
Canonical definitions of terminology matching the codebase.

### 2. Architecture Reference
- **[Application Platform Layer](file:///Users/sahilmangla/atlas/docs/architecture/application-platform.md)**: The public Atlas SDK boundary, commands, results, and exception contract.
- **[Client Adapter Layer](file:///Users/sahilmangla/atlas/docs/architecture/client-adapters.md)**: Presentation and transport bindings exposing the Atlas SDK to external execution environments.
- **[CLI Usage Guide](file:///Users/sahilmangla/atlas/docs/usage/cli.md)**: Usage documentation for the ATLAS CLI client adapter.
- **[Architecture Principles](file:///Users/sahilmangla/atlas/docs/architecture/architecture-principles.md)**: Core design values (e.g. Domain First, Dependency Inversion, Immutability).
- **[System Overview](file:///Users/sahilmangla/atlas/docs/architecture/system-overview.md)**: Product vision and the 11 major subsystems' boundaries and responsibilities.
- **[Layered Architecture](file:///Users/sahilmangla/atlas/docs/architecture/layered-architecture.md)**: Vertical execution flows and commit mutations across layers.
- **[Engineering Workflow](file:///Users/sahilmangla/atlas/docs/architecture/engineering-workflow.md)**: Lifecycles, objectives, and transition state machine rules.
- **[Workflow Stage Execution](file:///Users/sahilmangla/atlas/docs/architecture/workflow-stages.md)**: AI-assisted and human-driven stage responsibilities.
- **[Intelligence Layer](file:///Users/sahilmangla/atlas/docs/architecture/intelligence-layer.md)**: Coordination of AI integration services under constitutional safety boundaries.
- **[Engineering Knowledge Layer](file:///Users/sahilmangla/atlas/docs/architecture/engineering-knowledge-layer.md)**: Phase 13 knowledge boundaries, lifecycle, retrieval, and persistence.
- **[Multi-Protocol AI Runtime](file:///Users/sahilmangla/atlas/docs/architecture/multi-protocol-ai-runtime.md)**: Protocol factory, protocol adapters, and protocol-independent prompt execution.
- **[Domain Model](file:///Users/sahilmangla/atlas/docs/architecture/domain-model.md)**: The lightweight Project aggregate root and sub-aggregate boundaries.
- **[Persistence Architecture](file:///Users/sahilmangla/atlas/docs/architecture/persistence.md)**: Filesystem storage details, path resolution inversion, and compensating transaction rollbacks.
- **[Traceability](file:///Users/sahilmangla/atlas/docs/architecture/traceability.md)**: Immutable provenance chains connecting evidence down to commits.
- **[Engineering Constitution](file:///Users/sahilmangla/atlas/docs/architecture/engineering-constitution.md)**: Coding quality rules and review compliance policies.
- **[AI Constitution](file:///Users/sahilmangla/atlas/docs/architecture/ai-constitution.md)**: Core rules (e.g. statelessness, no direct mutations, schema checks) governing AI generation safety.
- **[Subsystem Extension Guide](file:///Users/sahilmangla/atlas/docs/architecture/extension-guide.md)**: Walkthrough for adding a new engineering lifecycle stage.
- **[Presentation Layer (Phase 14)](file:///Users/sahilmangla/atlas/docs/architecture/presentation-layer.md)**: The upper, non-engine layer composing typed immutable Views from the Atlas read-model API and rendering them to JSON/Markdown/CLI.
- **[Presentation Extension Guide](file:///Users/sahilmangla/atlas/docs/guides/presentation-extension-guide.md)**: Walkthrough for adding a new View kind to the presentation layer.
- **[Platform Layer (Phase 15)](file:///Users/sahilmangla/atlas/docs/architecture/platform-layer.md)**: The Capability Layer, Contract Layer, and Adapter Boundary formalizing the single doorway every client goes through before reaching an engine subsystem.

### 3. Architecture Decisions (ADRs)
- **[ADR-001: Architecture Baseline v1.0](file:///Users/sahilmangla/atlas/docs/decisions/adr-001-architecture-baseline-v1.md)**: Initial ADR locking the v1.0 design baseline.
- **[ADR-002: Application Platform Layer](file:///Users/sahilmangla/atlas/docs/decisions/adr-002-application-platform-layer.md)**: Canonical public SDK and composition-root decision.
- **[ADR-003: Engineering Knowledge Layer](file:///Users/sahilmangla/atlas/docs/decisions/adr-003-engineering-knowledge-layer.md)**: Phase 13 knowledge boundaries, review, and immutability rules.
- **[ADR-004: Platform Capability & Contract Layer](file:///Users/sahilmangla/atlas/docs/decisions/adr-004-platform-capability-contract-layer.md)**: Phase 15 Capability Layer, Contract Layer, and Adapter Boundary decision.

### 4. Architecture Diagrams
- **[Application Platform Layer](file:///Users/sahilmangla/atlas/docs/diagrams/application-platform.md)**
- **[Client Adapter Layer](file:///Users/sahilmangla/atlas/docs/diagrams/client-adapter-layer.md)**
- **[Subsystem Interactions](file:///Users/sahilmangla/atlas/docs/diagrams/system-overview.md)**
- **[Engineering Pipeline](file:///Users/sahilmangla/atlas/docs/diagrams/engineering-pipeline.md)**
- **[Proposal Lifecycle](file:///Users/sahilmangla/atlas/docs/diagrams/proposal-lifecycle.md)**
- **[Intelligence Layer Boundary](file:///Users/sahilmangla/atlas/docs/diagrams/intelligence-layer.md)**
- **[Repository & Rollback Flow](file:///Users/sahilmangla/atlas/docs/diagrams/repository-flow.md)**
- **[Domain & Traceability Links](file:///Users/sahilmangla/atlas/docs/diagrams/domain-relations.md)**
- **[Runtime Request Lifecycle](file:///Users/sahilmangla/atlas/docs/diagrams/request-lifecycle.md)**
- **[Multi-Protocol AI Runtime](file:///Users/sahilmangla/atlas/docs/diagrams/multi-protocol-ai-runtime.md)**
- **[Knowledge Lifecycle](file:///Users/sahilmangla/atlas/docs/diagrams/knowledge-lifecycle.md)**
- **[Knowledge Workflow Integration](file:///Users/sahilmangla/atlas/docs/diagrams/knowledge-workflow-integration.md)**
- **[Presentation Flow (Phase 14)](file:///Users/sahilmangla/atlas/docs/diagrams/presentation-flow.md)**: Atlas Facade to PlatformOrchestrationService to Collectors to Read Models to Views to Renderers to RenderResult.
- **[Platform Request Dispatch (Phase 15)](file:///Users/sahilmangla/atlas/docs/diagrams/platform-request-dispatch.md)**: `Atlas.handle(RequestEnvelope)` through Capability dispatch to `ResponseEnvelope`.
