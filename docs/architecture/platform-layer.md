# Phase 15: Platform Layer

## Purpose

This document describes the Phase 15 additions inside `atlas/`: the **Capability Layer** (`atlas/capabilities/`), the **Contract Layer** (`atlas/contracts/`), and the **Adapter Boundary** (`atlas/adapters/`). Together they formalize the single doorway every client -- CLI, IDE, MCP, and AI/agent callers alike -- goes through before reaching an engine subsystem.

Phase 15 is purely additive and internal restructuring. It does not change `engine/*`, `presentation/*`, the shape of `Command`/`Result` DTOs, or the Application Platform Layer boundary established in [ADR-002](../decisions/adr-002-application-platform-layer.md). Every existing public `Atlas` method keeps its exact signature and behavior.

## Responsibilities

- Decompose the `Atlas` facade into five narrow, independently-testable capability objects.
- Provide a versioned request/response envelope (`RequestEnvelope` / `ResponseEnvelope`) wrapping the existing Command/Result DTOs.
- Provide a stable, versioned error contract (`PlatformErrorCode` / `ErrorEnvelope`) mapped from every `ApplicationError` subclass.
- Provide a structural adapter contract (`PlatformAdapter`) and capability-negotiation manifest so any client can declare its identity and discover what the platform exposes.
- Add `Atlas.handle(RequestEnvelope) -> ResponseEnvelope` as the uniform dispatch entry point for out-of-process/protocol clients.

## Non-Responsibilities

- Capabilities do not implement business logic -- see the Capability Responsibility Rule below.
- This phase does not build real MCP, IDE, REST, or Desktop adapters (still scaffolded stubs).
- This phase does not implement capability-based authorization/scoping -- only the seam (`PlatformCapabilityManifest`) for it.

---

## The Capability Layer

`atlas/capabilities/` holds five capability classes, each a relocation of a cohesive slice of the pre-Phase-15 `Atlas` method bodies -- no behavior change:

| Capability | Responsibilities | Public methods | Delegates to |
|---|---|---|---|
| `ProjectCapability` | Project lifecycle | `create_project`, `load_project`, `list_projects`, `archive_project` | `ProjectCreationService`, `ProjectLoadingService`, `ProjectRegistryService`, `ProjectLifecycleService`, `WorkflowInitializationService` |
| `WorkflowCapability` | Workflow status/readiness, stage transitions | `get_workflow_status`, `transition_stage` | `WorkflowRepository`, `WorkflowTransitionService`, `WorkflowOrchestrationService.readiness_service` / `.knowledge_orchestration` |
| `WorkflowExecutionCapability` | AI proposal generation, approval, rejection | `execute_stage`, `approve_proposal`, `reject_proposal` | `WorkflowOrchestrationService.generate_proposal` / `.process_review_decision`, `ProposalRepository` |
| `KnowledgeCapability` | Listing and human review of knowledge candidates | `list_candidates`, `show_candidate`, `review_knowledge_candidate` | `KnowledgeOrchestrationService.list_candidates` / `.get_candidate`, `WorkflowOrchestrationService.process_knowledge_review` |
| `PresentationCapability` | Typed read models, composed views, rendering | `get_*_read_model` (5), `get_*_view` (5), `render` | Read-only repositories, `PlatformOrchestrationService`, `RendererRegistry` |

`WorkflowExecutionCapability` is named deliberately narrower than a generic "execution" concept -- it owns exactly AI proposal generation and the two proposal review decisions, nothing else.

`get_knowledge_read_model` is owned by `PresentationCapability`, not `KnowledgeCapability`: in the pre-Phase-15 code it lived in the same "Phase 14 typed read models" grouping as `get_project_read_model` et al., sourced directly from repositories, while `KnowledgeCapability` owns only the human review *action* (a command handler, like `execute_stage` or `approve_proposal`).

### Dependency Rules

```
clients/*            --X  atlas/capabilities/     (clients only ever see Atlas, per ADR-002)
atlas/_service.py     --> atlas/capabilities/*     (Atlas composes capabilities; capabilities never import Atlas)
atlas/capabilities/*  --> engine/*                 (same repos/services each capability already used inside Atlas)
atlas/capabilities/*  --X  atlas/capabilities/*    (no capability imports another -- no cross-coupling)
```

`PresentationCapability` owns its own copy of `_map_project_exception` rather than sharing `ProjectCapability`'s, specifically to avoid a runtime dependency between two capability instances -- a small, deliberate duplication in exchange for independence.

Every capability method that calls into `engine/*` must translate the engine-layer exceptions it can raise into `ApplicationError` subclasses before they cross the capability boundary -- `Atlas.handle()` only catches `ApplicationError`, so anything else escapes uncaught and breaks the `ErrorEnvelope` wire contract for out-of-process adapters (MCP, REST). `ProjectCapability.create_project` additionally performs a compensating rollback (`ProjectRepository.delete()`) if workflow initialization fails after the project record was already persisted, so a partial failure never leaves an orphaned, permanently-stuck project behind.

### Capability Responsibility Rule (Architectural Invariant)

> **Capabilities are platform orchestration boundaries. They are not business-logic owners.**
>
> A capability **may**: validate platform-level inputs; coordinate calls to existing engine services in the same sequence `Atlas` used before Phase 15; translate internal engine exceptions into `ApplicationError` subclasses; map platform contracts (Command -> Result, Result -> envelope); return platform DTOs.
>
> A capability **must not**: implement business rules or lifecycle invariants (those remain exclusively in `engine/*` services); duplicate domain logic; access persistence beyond what `Atlas` already did; bypass an existing service to reach a repository directly; become an alternative engine layer.
>
> Business logic remains exclusively inside existing engine services (`engine/project`, `engine/workflow`, `engine/knowledge`, `engine/ai`, etc.). Capabilities are intentionally thin delegation layers.

### `CapabilityName`

`atlas/capabilities/base.py` defines the single enum used to name capabilities anywhere they are referenced -- the adapter negotiation manifest and the ownership matrix above:

```python
class CapabilityName(StrEnum):
    PROJECT = "project"
    WORKFLOW = "workflow"
    WORKFLOW_EXECUTION = "workflow_execution"
    KNOWLEDGE = "knowledge"
    PRESENTATION = "presentation"
```

No other module duplicates these string literals.

---

## The Contract Layer

`atlas/contracts/` is part of the public SDK surface -- adapter authors import from here.

### Request / Response Envelope

`RequestEnvelope[TCommand]` / `ResponseEnvelope[TResult]` (`atlas/contracts/envelope.py`) wrap the existing `Command`/`Result` DTOs with an API version, a request id, and (for requests) the calling adapter's identity. `ResponseEnvelope` enforces exactly one of `result` / `error` via a model validator.

### Error Contract

`PlatformErrorCode` / `ErrorEnvelope` (`atlas/contracts/errors.py`) give every `ApplicationError` subclass a stable, versioned code. `_ERROR_CODE_MAP` is a single explicit literal `dict[type[ApplicationError], PlatformErrorCode]` -- no reflection.

`UNKNOWN_ERROR` exists **only** as a defensive fallback inside `to_error_envelope()`. Every concrete `ApplicationError` subclass has, and must always have, an explicit entry in `_ERROR_CODE_MAP`, enforced by `tests/contracts/test_errors.py::test_all_application_errors_mapped` -- a dedicated architectural test that fails whenever a new `ApplicationError` subclass is introduced without a corresponding mapping entry. Observing `UNKNOWN_ERROR` at runtime signals a programming defect (an unmapped exception type, or an `Atlas.handle()` call with an unrecognized `Command` type), never routine application behavior such as a not-found project or a failed validation -- those all have dedicated codes.

### Versioning

`atlas/contracts/version.py` defines `PLATFORM_API_VERSION` (semver, currently `"1.0.0"`), `SCHEMA_VERSION` (integer envelope-shape version), and `is_compatible(client_api_version)` (same-major-version compatibility check).

**Policy:** Commands and Results may only gain new optional fields with defaults within a major version. Removing a field, changing a field's type, or changing error-code semantics requires a `PLATFORM_API_VERSION` major bump. `SCHEMA_VERSION` changes only if `RequestEnvelope`/`ResponseEnvelope` themselves gain or lose required fields.

---

## The Adapter Boundary

`atlas/adapters/protocol.py` defines the structural contract any client satisfies:

- `AdapterKind` -- `CLI`, `IDE`, `MCP`, `AI`, `REST`, `DESKTOP`
- `AdapterContext` -- the identity (`kind`, `name`, `version`) a client presents to the platform
- `PlatformCapabilityManifest` -- what the platform tells an adapter it exposes (`capabilities: tuple[CapabilityName, ...]`, strongly typed, never raw strings)
- `PlatformAdapter` -- a `@runtime_checkable` `Protocol` with a `context` property and a `negotiate(atlas) -> PlatformCapabilityManifest` method. No adapter subclasses it; conformance is structural, verified via `isinstance()`.

`negotiate()` returns a **static** manifest in Phase 15 -- all five capabilities are always present. This is intentionally the seam for the already-documented future "capability-based authorization scopes" (see [Application Platform Layer](application-platform.md#future-extensions)), not an implementation of it.

---

## `Atlas.handle()` -- Usage Policy (Architectural Invariant)

**Named methods** (`create_project`, `execute_stage`, `get_project_dashboard_view`, etc.) **remain permanently supported** for the CLI adapter, test suites, internal tooling, and any direct SDK consumer in-process with the `Atlas` instance. They are **not deprecated** -- no scheduled removal, no `DeprecationWarning`.

**`Atlas.handle(RequestEnvelope)` is the preferred entry point** for MCP, REST, IDE integrations, AI agents, and any future out-of-process or protocol-driven adapter. This is architectural guidance, not runtime enforcement -- `Atlas` never rejects a named-method call from any caller type. Out-of-process/protocol adapters need `.handle()`'s envelope metadata (`request_id`, `api_version`, `adapter` identity) for serialization, logging, tracing, and version negotiation; in-process callers have no such need.

This keeps exactly **one explicit protocol boundary** (`Atlas.handle()`) for external/protocol adapters while preserving full backward compatibility for everything already calling named methods.

`Atlas.handle()` dispatches via `self._dispatch`, an explicit literal `dict[type[Command], Callable]` built once in `__init__` -- ten entries, one per `Command` subclass. No reflection, no `getattr`-by-name magic, consistent with the codebase's existing "explicit registration, no dynamic discovery" rule (already used for `ExtractorRegistry` in Phase 13 and `RendererRegistry` in Phase 14).

---

## The CLI Adapter (Retrofit)

`clients/cli/application.py` gained exactly three additions: an `AdapterContext` constructed at `__init__` time, a `context` property, and a `negotiate()` method returning the static five-capability manifest. `CLIApplication._dispatch()` is unchanged -- it still calls named `Atlas` methods directly, proving the adapter boundary is real without forcing a rewrite of the one adapter that already works. No `engine.*` import was introduced.

MCP, IDE, REST, and Desktop remain unbuilt stub packages. Any adapter built against them in a future phase is expected to implement `PlatformAdapter` and call through `Atlas.handle()`.

---

## Testing

- `tests/contracts/` -- envelope, error, and version contract tests, including the error-code completeness test.
- `tests/adapters/` -- `PlatformAdapter` protocol tests, including CLI conformance.
- `tests/test_atlas/test_platform_handle.py` -- `Atlas.handle()` equivalence tests against named methods, for every Command type, plus the unknown-command and error-mapping edge cases.
- `tests/architecture/test_platform_boundaries.py` -- AST-based static import-boundary checks: capabilities never import each other, contracts/adapters never import `engine.*`/`presentation.*`, clients never import `atlas.capabilities` (except the shared `CapabilityName` enum), CLI still never imports `engine.*`.
- `tests/support/test_platform_bootstrap.py` -- extended with a non-regression check that `_dispatch` stays a literal dict, never dynamic `getattr`-by-name lookup.

See also [Platform Request Dispatch Diagram](../diagrams/platform-request-dispatch.md) and [ADR-004](../decisions/adr-004-platform-capability-contract-layer.md).
