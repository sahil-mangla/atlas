# ADR-001: Establish ATLAS v1.0 Architecture Baseline

## Status
Approved

## Context
ATLAS has successfully completed development through Phase 7, followed by stabilization phases 6.5 and 7.5. Before Phase 8 begins, the platform requires a canonical, consolidated engineering reference documenting the v1.0 structural baseline. This is necessary to prevent regression, preserve architectural boundaries, guide new developers/agents, and establish the ground truth for subsequent design decisions.

## Decision
We will establish a standardized documentation structure under the `docs/` directory to serve as the baseline architectural reference. This includes:
1. Canonical documentation of subsystem concerns, layered executions, transition lifecycles, and persistence patterns.
2. Formalizing the **Engineering Constitution** and **AI Constitution** within the docs to serve as permanent validation rules.
3. Establishing this document as **ADR-001**, which initiates the numbered Architectural Decision Record chain for the ATLAS project.

## Consequences
- **Design Baseline Locked**: The core design patterns (Domain First, Explicit Dependencies, Stateless AI Generation, and Compensating filesystem Rollback) are recognized as the approved v1.0 baseline.
- **Scaffolding Requirements**: Any subsequent subsystems or stage modifications must be documented first in the `Blueprint` directory and comply with the extension rules defined in the docs.
- **ADR Maintenance**: Future architectural changes must be registered under `docs/decisions/` following the sequential naming convention (e.g. `docs/decisions/adr-002-feature-name.md`).
