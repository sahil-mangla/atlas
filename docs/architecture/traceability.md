# ATLAS Traceability Architecture

## Purpose
This document defines the traceability architecture of the ATLAS platform. It outlines the structural lineage connecting conceptual project definitions down to code commits and explains the implementation patterns used to enforce provenance.

## Responsibilities
- Define the sequential pipeline linking evidence, findings, design decisions, and tasks.
- Detail the lightweight Pydantic value objects used to construct traceability chains.
- Document the separation between domain model definitions and validation services.

## Non-Responsibilities
- Describing Git version control graphs or commit hash formatting rules.
- Detailing the graphical user interface components used to display traceability trees.

---

## The Traceability Lineage

ATLAS guarantees an unbroken, audited path of design and implementation provenance, ensuring that every code change or roadmap task has a clear upstream engineering justification. The lineage progresses as follows:

```
    Evidence (Research source citations and domain logs)
       ↓
    Finding (Synthesized facts derived from evidence)
       ↓
    Opportunity (Identified design directions and feature proposals)
       ↓
    Planning (Task roadmaps and milestones mapped to opportunities)
       ↓
    Architecture (Subsystem components and ADRs informed by planning)
       ↓
    Evaluation (Audits verifying implementation conformance to designs)
       ↓
    Proposal (AI-drafted modifications referencing context snapshots)
       ↓
    Commit (Approved and versioned snapshots committed to the workspace)
```

---

## Enforcing Traceability in Code

Traceability is modeled and enforced using two primary patterns in the domain layer:

### 1. The Traceability Link Model
The `TraceabilityLink` (`engine/domain/traceability.py`) is a lightweight value object composed of:
- `source_id`: The unique UUID of the upstream originating concept (e.g. the specific `Evidence` or `ResearchFinding` ID).
- `description`: An optional text string explaining the nature of the relationship or dependency justification.

### 2. Decoupled Validation
To preserve the purity of the domain models and prevent database lookups within Pydantic structures:
- `TraceabilityLink` acts as a passive container and does not perform database verification during initialization.
- Existence validation of target UUIDs is delegated to downstream validation services (such as `ArtifactValidationService`). This keeps the core domain models decoupled from global persistence contexts and simplifies testing.

---

## Future Extensions
- Dynamic compliance checking that blocks proposal commits if the underlying traceability links reference unapproved or archived source documents.
- Automated dependency graph exporters generating visual trace directories directly from persisted metadata.
