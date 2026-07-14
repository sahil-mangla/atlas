# ATLAS Domain Model

## Purpose
This document defines the core domain model structures of the ATLAS platform. It outlines the role of the `Project` aggregate root, details the sub-aggregate boundaries, and explains the mechanisms used for snapshot versioning and lifecycle tracking.

## Responsibilities
- Establish the structural model boundaries of the ATLAS system.
- Detail the lightweight ID-based references connecting the Project root to sub-aggregates.
- Document snapshot representations and artifact metadata composition.

## Non-Responsibilities
- Describing filesystem serialization details or database schema definitions.
- Detailing utility functions, helper methods, or validation scripts inside python classes.

---

## The Project Aggregate Root

The `Project` model (`engine/domain/project.py`) is the root boundary of the system context. It governs the complete engineering project lifecycle:

- **Lightweight Reference Pattern**: To prevent circular coupling and avoid loading large nested structures, the `Project` aggregate does not embed sub-aggregates directly. Instead, it holds reference identifiers (UUIDs) for:
  - `workspace_id`
  - `planning_id`
  - `architecture_id`
  - `research_id`
  - `memory_id`
  - `workflow_id`
  - `evaluation_ids` (a list of historical evaluation UUIDs)

- **Operational States**: The project status (`ProjectStatus`) manages lifecycle phases:
  - `INITIALIZED`: Newly created, blank project templates.
  - `ACTIVE`: Actively undergoing planning, architecture, or coding.
  - `PAUSED`: Execution state and configuration logs frozen.
  - `ARCHIVED`: Permanent read-only archive; no modifications permitted.

---

## Sub-Aggregate Boundaries

ATLAS decomposes engineering concerns into independent sub-aggregates, each with clearly defined boundaries:

- **Workspace**: Governs the physical directory structures, workspace files, and local file configurations.
- **Research**: Captures the problem definition, raw evidence logs, domain findings, constraints, assumptions, and opportunities.
- **Planning**: Manages the scoping limits, milestones list, epic divisions, granular tasks, and subtasks.
- **Architecture**: Controls system component specs, data definitions, external dependencies, and Architectural Decision Records (ADRs).
- **Workflow**: Manages the active objectives checklist, state validations, and the immutable transition history.
- **Memory**: Tracks conversation dialogue logs, memory entries, and session contexts.
- **Evaluation**: Performs functional reviews, checks requirements coverage, and logs compliance findings.

---

## Snapshot Versioning & Artifact Metadata

To track modifications and maintain history, ATLAS uses standard versioned snapshot wrappers composed with standard metadata:

### 1. Snapshot Models
Each major aggregate supports snapshot freezes (e.g., `ResearchSnapshot`, `PlanningSnapshot`, `ArchitectureSnapshot`, `EvaluationSnapshot`). A snapshot represents a complete, immutable freeze of the aggregate's domain state.

### 2. Artifact Metadata Composition
Rather than using deep inheritance, every canonical engineering artifact and snapshot composes `ArtifactMetadata` (`engine/domain/metadata.py`) to handle provenance:
- `id`: Unique UUID.
- `version`: Monotonically increasing version counter.
- `created_at`: UTCDatetime stamp.
- `created_by`: Name of the creator (human or agent ID).
- `status`: Lifecycle status (`DRAFT`, `REVIEW`, `APPROVED`, `ARCHIVED`).

---

## Future Extensions
- Support for concurrent workspace branches matching Git commits, enabling parallel developer state tracking.
- Automated API-driven export of complete domain trees into OpenAPI and GraphQL metadata schemas.
