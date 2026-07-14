# ADR-002: Formalize Application Platform Layer (Atlas SDK)

## Status
Approved

## Context
During Phase 8 refinement, the decision was made that ATLAS is a local engineering platform, not a standalone client application. The platform is designed to be consumed by first-party and third-party adapters (CLI, IDE, Web, MCP). To ensure stability, security, and decoupling, the platform requires a strict public boundary. Without a canonical Application Platform Layer, clients would have to couple directly to internal engine domain services, risking breaking changes and violating architectural layers.

## Decision
We establish the `atlas/` package as the canonical public SDK and Application Platform Layer for ATLAS. This layer acts as a Facade and implements a strict Command-Result pattern.

1. **Strict Client Boundary**: No client (CLI, IDE, etc.) may bypass the Application Layer. Direct imports from `engine/` by clients are prohibited.
2. **Command-Result Pattern**: All interactions across the boundary use immutable Command DTOs and return pure Result DTOs.
3. **Explicit Exception Mapping**: All internal `engine/` exceptions are caught and explicitly mapped to public application errors (e.g., `ProjectNotFoundError`) within the `atlas/` package.
4. **Hidden Composition Root**: The bootstrapping logic (`_bootstrap.py`) is hidden inside the `atlas/` package and is responsible for wiring all repositories and internal services.

## Consequences
- **Stable Public API**: We can refactor internal engine components heavily without breaking client integrations, as long as the Command/Result signatures remain unchanged.
- **Client Decoupling**: Clients become extremely thin, knowing nothing about internal Workflow Orchestration or Domain aggregates.
- **Testing**: We can now write high-level integration tests exclusively against the public `Atlas` facade, verifying the platform as a whole from the outside in.
