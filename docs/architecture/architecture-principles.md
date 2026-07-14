# ATLAS Architecture Principles

## Purpose
This document defines the primary architectural principles that govern the design, structural boundaries, and technology-independent decisions of the ATLAS platform. These principles ensure that the system remains modular, understandable, and extensible as it scales.

## Responsibilities
- Establish the core values guiding system component relationships and dependency structures.
- Detail the rules for handling domain logic, persistence, and intelligence interfaces.
- Align code implementation structures with the ATLAS Engineering Constitution and AI Constitution.

## Non-Responsibilities
- Defining language-specific syntax styles, formatting choices, or formatting tools (which are delegated to Ruff/mypy).
- Detailing specific database schema configurations or hardware deployment targets.

---

## Core Architectural Principles

### 1. Domain First
Domain modeling establishes a shared, conceptual understanding of the problem space independent of technologies. All system structures, dependencies, and business logic flow from the core domain entities (`engine/domain/`). Frameworks, libraries, and databases are treated as outer-ring adapters.

### 2. Explicit Dependencies
Dependencies, configuration parameters, and execution contexts must be declared explicitly. The use of global singletons, shared mutable state, or implicit environments is prohibited. Subsystems must request dependencies from the outside (typically via constructor injection).

### 3. Composition over Inheritance
We prefer composition—combining focused, lightweight structures (such as composing `ArtifactMetadata` into snapshots)—rather than deep class hierarchies. This keeps components flexible, reduces refactoring friction, and prevents base-class changes from causing cascading breaks.

### 4. Dependency Inversion
High-level policy modules (like services and orchestrators) must not depend on low-level detail modules (like storage adapters). Both must depend on abstractions (abstract base classes or interfaces). This separates business rules from infrastructure details (e.g. `FilesystemArchitectureRepository` implementing `ArchitectureRepository`).

### 5. Immutable Snapshots
State mutations do not happen incrementally on active records. Instead, state transitions result in versioned, immutable snapshots (e.g., `ResearchSnapshot`, `ArchitectureSnapshot`). Once created and approved, a snapshot is frozen and committed to disk, serving as a permanent historical record.

### 6. Versioned Engineering Artifacts
Every major artifact composed in the ATLAS workspace inherits a standard identification, versioning, and status schema using `ArtifactMetadata`. This guarantees uniform identity tracking, sequential version increments, and lifecycle state management across all subsystems.

### 7. Human Approval Principle
Automated systems and AI agents cannot unilaterally execute lifecycle stage transitions or commit modifications. Every transition and proposal commit requires explicit human review, authorization, and approval. Engineering judgment belongs to the human developer.

### 8. Deterministic Workflows
Workflow progression is governed by a strict state machine (`WorkflowTransitionService`) with predefined stages, transition boundaries, and required objectives. This guarantees a predictable, repeatable progression through the software development lifecycle.

### 9. AI as Assistant
Artificial Intelligence is an executing partner, not an architectural authority. AI systems must operate within predefined constraints, generating stateless proposals (`AIProposal`) that undergo semantic validation and human audit before modifying system state.

### 10. Traceability by Design
The platform enforces a continuous lineage linking upstream elements down to commits. Every engineering change must map back to an architectural design, which maps to a task milestone, which maps to research findings and raw evidence (`TraceabilityLink`).

---

## Future Extensions
- Automated static validation of imports to ensure code modules do not violate the Domain First and Dependency Inversion boundaries.
- Live ADR compliance checking that compares code files directly against active architectural constraints during validation pipelines.
