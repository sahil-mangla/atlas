# ADR-004: Platform Capability, Contract, and Adapter Boundary Layer

## Status
Approved

## Context

ADR-002 established `atlas/` as the canonical Application Platform Layer -- a single `Atlas` facade using the Command-Result pattern. By Phase 14, `Atlas` had grown to own project lifecycle, workflow status/transitions, AI proposal execution, knowledge review, and the full Phase 14 read-model/view/render surface, all as flat methods on one class.

At the same time, only the CLI adapter is implemented; MCP, IDE, REST, and Desktop remain scaffolded stubs. Before those adapters are built, the platform needs an explicit, versioned, testable contract that *every* client -- present or future, in-process or out-of-process -- is forced through, plus internal seams that keep `Atlas` itself maintainable as its surface grows.

## Decision

We introduce three new, purely additive internal packages inside `atlas/`, plus one new public method on `Atlas`:

1. **Capability Layer (`atlas/capabilities/`, internal).** `Atlas`'s existing method bodies are decomposed into five capability classes -- `ProjectCapability`, `WorkflowCapability`, `WorkflowExecutionCapability`, `KnowledgeCapability`, `PresentationCapability` -- each a pure relocation of the exact logic `Atlas` already ran. Every `Atlas` public method becomes a one-line forward. No behavior changes.

   **Capability Responsibility Rule (locked):** Capabilities are platform orchestration boundaries, not business-logic owners. A capability may validate platform inputs, coordinate existing services, translate exceptions, map contracts, and return platform DTOs. A capability must never implement business rules, duplicate domain logic, access persistence beyond what `Atlas` already did, bypass a service to reach a repository, or become an alternative engine layer. Business logic remains exclusively inside existing `engine/*` services.

   `WorkflowExecutionCapability` (not "ExecutionCapability") is named to reflect its narrow, actual scope: AI proposal generation and the two proposal review decisions -- nothing broader.

   `CapabilityName` (`atlas/capabilities/base.py`) is the single `StrEnum` naming all five capabilities; it is reused by the adapter negotiation manifest so no raw capability-name strings exist anywhere in the platform.

2. **Contract Layer (`atlas/contracts/`, public).** `RequestEnvelope[TCommand]` / `ResponseEnvelope[TResult]` wrap the existing `Command`/`Result` DTOs with a request id, API version, and adapter identity, without changing their shape. `PlatformErrorCode` / `ErrorEnvelope` give every `ApplicationError` subclass a stable, versioned error code via a single explicit `_ERROR_CODE_MAP` literal. `PLATFORM_API_VERSION` / `SCHEMA_VERSION` / `is_compatible()` govern wire-contract compatibility.

   `UNKNOWN_ERROR` is a defensive-fallback-only code. Every concrete `ApplicationError` subclass must have an explicit entry in `_ERROR_CODE_MAP`; a dedicated test (`test_all_application_errors_mapped`) fails the build if a new subclass is added without one. `UNKNOWN_ERROR` reaching a caller signals a programming defect, never routine application behavior.

3. **Adapter Boundary (`atlas/adapters/`, public).** `PlatformAdapter` is a `@runtime_checkable` structural `Protocol` (no inheritance) that any client satisfies by exposing a `context: AdapterContext` property and a `negotiate(atlas) -> PlatformCapabilityManifest` method. The manifest is static in Phase 15 (all five capabilities always present) -- the seam for future capability-based authorization scoping, not an implementation of it.

4. **`Atlas.handle(RequestEnvelope) -> ResponseEnvelope`** is added as a new public method, dispatching via an explicit literal `dict[type[Command], Callable]` built once in `__init__`.

   **Usage policy (locked):** Named `Atlas` methods remain permanently supported -- not deprecated -- for the CLI adapter, test suites, internal tooling, and any in-process direct SDK consumer. `Atlas.handle()` is the *preferred* (not enforced) entry point for MCP, REST, IDE, AI-agent, and any future out-of-process/protocol-driven adapter, because those callers need the envelope's request id, API version, and adapter identity for serialization, logging, tracing, and version negotiation that in-process callers do not need.

The CLI adapter (`clients/cli/application.py`) is retrofitted minimally: it gains an `AdapterContext`, a `context` property, and a `negotiate()` method, proving structural `PlatformAdapter` conformance. Its internal dispatch loop is unchanged -- it continues calling named `Atlas` methods.

## Consequences

- **Zero behavior change, zero breaking change.** Every existing `Atlas` method keeps its exact signature; `engine/*` and `presentation/*` are untouched (verified by a zero-diff check); `_AtlasServices` and all Command/Result DTOs are unchanged.
- **A maintainable seam for `Atlas`'s continued growth.** New capabilities can be added without every method living on one flat class, while the Capability Responsibility Rule prevents that seam from becoming a second engine layer.
- **A stable wire contract for future adapters.** MCP, IDE, REST, and Desktop adapters, when built, have a versioned envelope, a stable error contract, and a structural conformance test to build against -- without this phase having to build them.
- **Testability.** Capability behavior-equivalence tests, contract round-trip tests, an error-code completeness test, and AST-based boundary tests (capabilities never import each other, contracts/adapters never import `engine.*`, clients never import `atlas.capabilities` except the shared naming enum) are all new and passing.
