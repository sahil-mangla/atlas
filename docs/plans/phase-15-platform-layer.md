# Phase 15: Platform Layer — Capability, Contract, and Adapter Boundary — Implementation Plan

**Status:** Implemented — post-implementation audit passed with one fix applied
**Scope:** Originally planning-only; implemented and audited in the same engagement
**Baseline:** Phases 1–14 complete and locked
**Target location:** `atlas/capabilities/`, `atlas/contracts/`, `atlas/adapters/` (all new, additive to `atlas/`)

**Post-implementation corrigendum:** the pre-implementation draft below stated the `Atlas.handle()` dispatch table would have "nine" entries. `atlas/commands.py` in fact defines **ten** `Command` subclasses (the draft undercounted by one). All references below have been corrected to ten to match the as-built code and tests; this correction was identified and applied during the Phase 15 post-implementation audit.

---

## 1. Executive Summary

### Overall Objective

Introduce a formal **Platform Layer** inside the existing `atlas/` package so that **every** client — CLI, IDE, MCP, and AI/agent callers alike — is forced through one explicit, versioned, contract-tested boundary before it ever reaches an engine subsystem. This phase does not create new engine capability, does not touch `engine/*`, and does not add new client adapters (MCP/IDE/Desktop/REST remain scaffolded stubs). It formalizes and hardens what already exists as the `Atlas` facade into three explicit internal seams:

1. **Capability Layer** — the `Atlas` facade decomposed into five narrow, independently testable capability objects, each owning one cohesive slice of the existing public surface.
2. **Contract Layer** — explicit, versioned request/response envelopes and a stable error contract, wrapping the existing Command/Result DTOs without changing their shape.
3. **Adapter Boundary** — a structural protocol (`PlatformAdapter`) that any client (present or future) must satisfy, plus a capability-negotiation manifest, so the platform can tell what any given caller is and what it declares support for.

This is **purely internal restructuring plus additive surface**. Every existing public method on `Atlas` (`create_project`, `execute_stage`, `get_project_dashboard_view`, etc.) keeps its exact signature and behavior. Nothing that imports `atlas` today breaks.

### Architectural Impact

Phase 15 does not change the dependency direction established in Phases 1–14. It adds one new internal seam **inside** the already-locked boundary:

```
Client (CLI / IDE / MCP / AI / REST / Desktop)
        │
        ├─► [existing] Atlas.<named method>(Command) -> Result      (unchanged, still valid)
        │
        └─► [NEW]      Atlas.handle(RequestEnvelope) -> ResponseEnvelope
                              │
                              ▼
                        Capability Layer (atlas/capabilities/)
                              │
                              ▼
                Existing Phase 1-14 services / repositories / orchestration
                        (WorkflowOrchestrationService, KnowledgeOrchestrationService,
                         PlatformOrchestrationService, project/research/planning/
                         architecture/evaluation services — ALL UNCHANGED)
```

**What does not change:**

- `engine/*` subsystems (ai, architecture, domain, evaluation, knowledge, memory, planning, project, prompt, research, workflow) — zero modifications, zero new imports into them, zero new imports out of them.
- `presentation/*` — zero modifications. `PresentationCapability` simply relocates existing `Atlas` read-model/view/render methods; it calls the exact same `PlatformOrchestrationService` and repositories Phase 14 already wired.
- `Command` / `Result` DTO shapes in `atlas/commands.py` and `atlas/results.py` — unchanged. The new envelope wraps them; it does not replace them.
- `atlas/_bootstrap.py` composition-root **role** — still the sole place that constructs repositories and services and the sole caller of `Atlas.__init__` / `Atlas._bind_presentation`. Its construction *sequence* gains no new steps (see §8).
- The two-phase presentation-bind dance documented in `docs/architecture/presentation-layer.md` (Atlas built from `_AtlasServices` → collectors/orchestration built from the live Atlas → `_bind_presentation` attaches them) — preserved exactly, just relocated behind `PresentationCapability._bind(...)`.

**What is new:**

| Concern | New home | Nature |
|---|---|---|
| Capability decomposition of `Atlas` | `atlas/capabilities/` | Internal-only; not imported by clients directly |
| Request/response envelope, versioning | `atlas/contracts/` | Public SDK surface — importable by adapters |
| Error contract (stable codes) | `atlas/contracts/errors.py` | Public SDK surface |
| Adapter structural contract | `atlas/adapters/` | Public SDK surface — importable by adapter authors |
| Uniform dispatch entrypoint | `Atlas.handle()` | New public method on the existing facade |

### Scope

**In scope:**

- Decompose `Atlas`'s existing method bodies into five capability classes (no behavior change).
- Define `RequestEnvelope[T]` / `ResponseEnvelope[T]` contract types wrapping existing Commands/Results.
- Define a stable `PlatformErrorCode` enum + `ErrorEnvelope`, with an explicit, exhaustively-tested mapping from every existing `ApplicationError` subclass.
- Define `PLATFORM_API_VERSION` (semver) and `SCHEMA_VERSION` (envelope shape version) with a compatibility check function.
- Define the `PlatformAdapter` structural protocol, `AdapterContext`, `AdapterKind`, and `PlatformCapabilityManifest`.
- Add `Atlas.handle(envelope) -> ResponseEnvelope` as a single explicit dispatch table over existing capability methods.
- Retrofit the CLI adapter (`clients/cli/application.py`) minimally to declare an `AdapterContext` and prove `PlatformAdapter` conformance — **without** requiring it to switch its internal dispatch from named methods to `.handle()`.
- Contract tests, capability-boundary tests, adapter-conformance tests.
- Documentation: new architecture doc, new ADR, new diagram, updates to existing docs.

**Out of scope:**

- Building real MCP, IDE, REST, or Desktop adapters (still scaffolded stubs — future phases).
- Capability-based authorization / scoping (explicitly named as "Future Extensions" in `docs/architecture/application-platform.md` already; this phase lays the seam, does not implement authorization).
- Event streams / subscriptions (also already listed as future work; unaffected).
- Any change to engine subsystem boundaries, domain models, or persistence formats.
- Migrating the CLI's internal dispatch loop to the envelope path — it may continue calling named `Atlas` methods directly.

### User Review Items

1. Confirm the five-capability split (Project / Workflow / Execution / Knowledge / Presentation) matches how the team wants to reason about the platform boundary (§3).
2. Confirm `Atlas.handle()` coexists permanently with the named methods, rather than the named methods becoming thin deprecated wrappers scheduled for removal (§6.3 — recommended: coexist permanently, no deprecation).
3. Confirm `PLATFORM_API_VERSION` starts at `1.0.0` (reflecting that the wire contract is being formalized now, not that this is a breaking change to existing consumers).
4. Confirm `retryable` on `ErrorEnvelope` is populated only for `AIProviderError` in this phase (the only genuinely transient failure mode today); all others `False`.

### Open Questions

1. Should `AdapterContext.version` be validated as semver at construction, or treated as an opaque string until a second adapter exists to compare against? (Recommended: opaque string now; add semver validation when the MCP/IDE adapters are built and a real compatibility policy is needed.)
2. Should `Atlas.handle()` accept a raw `Command` as a convenience overload in addition to a full `RequestEnvelope`? (Recommended: no — the envelope is the point; convenience would erode the "one doorway" guarantee for out-of-process adapters.)

---

## 2. Contract Design

### 2.1 Request / Response Envelope

New module `atlas/contracts/envelope.py`:

```python
from typing import Generic, TypeVar
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field

from atlas.adapters.protocol import AdapterContext
from atlas.contracts.version import PLATFORM_API_VERSION

TCommand = TypeVar("TCommand", bound="Command")
TResult = TypeVar("TResult", bound="Result")


class RequestEnvelope(BaseModel, Generic[TCommand]):
    """Versioned, adapter-attributed wrapper around an existing Command DTO."""

    model_config = ConfigDict(frozen=True)

    api_version: str = PLATFORM_API_VERSION
    request_id: UUID = Field(default_factory=uuid4)
    adapter: AdapterContext
    command: TCommand


class ResponseEnvelope(BaseModel, Generic[TResult]):
    """Versioned wrapper around an existing Result DTO or an ErrorEnvelope."""

    model_config = ConfigDict(frozen=True)

    api_version: str = PLATFORM_API_VERSION
    request_id: UUID
    result: TResult | None = None
    error: "ErrorEnvelope | None" = None
```

Exactly one of `result` / `error` is populated per response — enforced by a Pydantic model validator, not by convention. `RequestEnvelope`/`ResponseEnvelope` are pure wrappers: they carry no business logic and never appear inside `engine/*`.

### 2.2 Error Contract

New module `atlas/contracts/errors.py`:

```python
from enum import StrEnum
from pydantic import BaseModel, ConfigDict

from atlas.exceptions import (
    AIProviderError, ApplicationError, BootstrapError, ContextAssemblyError,
    InvalidProjectError, InvalidTransitionError, ProjectAlreadyExistsError,
    ProjectLifecycleError, ProjectNotFoundError, ProposalValidationError,
    StageExecutionError, WorkflowNotReadyError,
)


class PlatformErrorCode(StrEnum):
    PROJECT_NOT_FOUND = "project_not_found"
    PROJECT_ALREADY_EXISTS = "project_already_exists"
    INVALID_PROJECT = "invalid_project"
    PROJECT_LIFECYCLE_ERROR = "project_lifecycle_error"
    WORKFLOW_NOT_READY = "workflow_not_ready"
    INVALID_TRANSITION = "invalid_transition"
    STAGE_EXECUTION_ERROR = "stage_execution_error"
    PROPOSAL_VALIDATION_ERROR = "proposal_validation_error"
    CONTEXT_ASSEMBLY_ERROR = "context_assembly_error"
    AI_PROVIDER_ERROR = "ai_provider_error"
    BOOTSTRAP_ERROR = "bootstrap_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: PlatformErrorCode
    message: str
    retryable: bool = False


# Single explicit literal mapping -- no reflection, no dynamic lookup.
_ERROR_CODE_MAP: dict[type[ApplicationError], PlatformErrorCode] = {
    ProjectNotFoundError: PlatformErrorCode.PROJECT_NOT_FOUND,
    ProjectAlreadyExistsError: PlatformErrorCode.PROJECT_ALREADY_EXISTS,
    InvalidProjectError: PlatformErrorCode.INVALID_PROJECT,
    ProjectLifecycleError: PlatformErrorCode.PROJECT_LIFECYCLE_ERROR,
    WorkflowNotReadyError: PlatformErrorCode.WORKFLOW_NOT_READY,
    InvalidTransitionError: PlatformErrorCode.INVALID_TRANSITION,
    StageExecutionError: PlatformErrorCode.STAGE_EXECUTION_ERROR,
    ProposalValidationError: PlatformErrorCode.PROPOSAL_VALIDATION_ERROR,
    ContextAssemblyError: PlatformErrorCode.CONTEXT_ASSEMBLY_ERROR,
    AIProviderError: PlatformErrorCode.AI_PROVIDER_ERROR,
    BootstrapError: PlatformErrorCode.BOOTSTRAP_ERROR,
}
_RETRYABLE: frozenset[type[ApplicationError]] = frozenset({AIProviderError})


def to_error_envelope(exc: ApplicationError) -> ErrorEnvelope:
    code = _ERROR_CODE_MAP.get(type(exc), PlatformErrorCode.UNKNOWN_ERROR)
    return ErrorEnvelope(
        code=code, message=str(exc), retryable=type(exc) in _RETRYABLE
    )
```

**Completeness rule (enforced by test, §9.4):** every concrete subclass of `ApplicationError` defined in `atlas/exceptions.py` must appear as a key in `_ERROR_CODE_MAP`. A new exception type added later without a mapping entry fails CI, not silently falls back to `UNKNOWN_ERROR` in production.

**`UNKNOWN_ERROR` — architectural intent (invariant, locked for Phase 15).** This code exists **only** as a defensive fallback inside `to_error_envelope()`'s `.get(type(exc), PlatformErrorCode.UNKNOWN_ERROR)` call — it is not a normal, expected outcome of any documented application error path. Every concrete `ApplicationError` subclass has, and must always have, an explicit entry in `_ERROR_CODE_MAP`; the completeness test in §9.4 (`test_all_application_errors_mapped`) is a dedicated architectural test that fails the build whenever a new `ApplicationError` subclass is introduced without a corresponding mapping entry, so `UNKNOWN_ERROR` is never reached via any exception type that exists in the codebase today or is added correctly in the future. If `UNKNOWN_ERROR` is ever observed at runtime, it signals a programming defect (a raised `ApplicationError` subclass that was added without updating `_ERROR_CODE_MAP` and without the completeness test catching it, or an `Atlas.handle()` call with an unrecognized `Command` type per §4.1) — never routine application behavior such as a not-found project or a failed validation, which all have dedicated codes. This rule must be reproduced in `docs/decisions/adr-004-platform-capability-contract-layer.md` and `docs/architecture/platform-layer.md` (§10). No runtime behavior changes as a result of documenting this.

### 2.3 Versioning

New module `atlas/contracts/version.py`:

```python
PLATFORM_API_VERSION = "1.0.0"   # semver: the wire-contract version clients negotiate against
SCHEMA_VERSION = 1                 # integer envelope-shape version; bumped only on breaking envelope changes


def is_compatible(client_api_version: str) -> bool:
    """Same major version => compatible. Additive (minor/patch) changes never break this."""
    return client_api_version.split(".", 1)[0] == PLATFORM_API_VERSION.split(".", 1)[0]
```

**Versioning policy (documented in `docs/architecture/platform-layer.md`, §10):**

- Commands and Results may only gain new **optional** fields with defaults within a major version — this is already the pattern used in Phase 13/14 (`pending_knowledge_candidates`, `research_repo | None`, etc.); Phase 15 makes it an explicit, written rule rather than an implicit convention.
- Removing a field, changing a field's type, or changing error-code semantics requires a `PLATFORM_API_VERSION` major bump.
- `SCHEMA_VERSION` governs the envelope's own shape (not the payload). It changes only if `RequestEnvelope`/`ResponseEnvelope` themselves gain/lose required fields.
- Adapters call `is_compatible()` during negotiation (§2.4) before assuming any specific Command/Result shape.

### 2.4 Adapter Structural Contract

New module `atlas/adapters/protocol.py`:

```python
from enum import StrEnum
from typing import Protocol, runtime_checkable
from pydantic import BaseModel, ConfigDict


class AdapterKind(StrEnum):
    CLI = "cli"
    IDE = "ide"
    MCP = "mcp"
    AI = "ai"
    REST = "rest"
    DESKTOP = "desktop"


class AdapterContext(BaseModel):
    """Identity a client presents to the platform on every request."""

    model_config = ConfigDict(frozen=True)

    kind: AdapterKind
    name: str
    version: str


class PlatformCapabilityManifest(BaseModel):
    """What the platform tells an adapter it exposes, at the negotiated API version."""

    model_config = ConfigDict(frozen=True)

    api_version: str
    capabilities: tuple[CapabilityName, ...]   # e.g. (CapabilityName.PROJECT, CapabilityName.WORKFLOW, ...)


@runtime_checkable
class PlatformAdapter(Protocol):
    """Structural contract every client adapter satisfies. No adapter subclasses
    this -- conformance is structural (duck-typed), verified via isinstance()
    against @runtime_checkable, matching the project's existing preference for
    explicit composition over inheritance hierarchies."""

    @property
    def context(self) -> AdapterContext: ...

    def negotiate(self, atlas: "Atlas") -> PlatformCapabilityManifest: ...
```

`negotiate()` returns a **static** manifest in Phase 15 — all five capabilities are always present; this is intentionally the seam for the already-documented future "capability-based authorization scopes" (`docs/architecture/application-platform.md`, Future Extensions), not an implementation of it.

`PlatformCapabilityManifest.capabilities` is strongly typed as `tuple[CapabilityName, ...]` — never raw strings — where `CapabilityName` is the single enum defined in `atlas/capabilities/base.py` (§3.1) and reused here without duplication. This removes magic strings from the adapter-negotiation surface entirely.

---

## 3. Capability Layer

### 3.0 `CapabilityName` — Single Source of Truth

`atlas/capabilities/base.py` defines the one enum used to name capabilities anywhere they are referenced — the manifest (§2.4), the ownership matrix (§3.4), and each capability class's self-identification:

```python
from enum import StrEnum


class CapabilityName(StrEnum):
    PROJECT = "project"
    WORKFLOW = "workflow"
    WORKFLOW_EXECUTION = "workflow_execution"
    KNOWLEDGE = "knowledge"
    PRESENTATION = "presentation"
```

No other module defines or duplicates these string literals. `atlas/adapters/protocol.py` imports `CapabilityName` from `atlas/capabilities/base.py` (a narrow, one-directional import of a pure enum — not a violation of the "adapters never import capabilities" dependency rule in §3.2, since `base.py` contains no capability logic, only the naming enum shared by both layers).

### 3.1 Package Structure

```
atlas/capabilities/
├── __init__.py                       # exports the 5 capability classes only
├── base.py                           # CapabilityName enum (used by the manifest, §2.4)
├── project_capability.py             # ProjectCapability
├── workflow_capability.py            # WorkflowCapability
├── workflow_execution_capability.py  # WorkflowExecutionCapability
├── knowledge_capability.py           # KnowledgeCapability
└── presentation_capability.py        # PresentationCapability
```

### 3.2 Dependency Rules

```
clients/*            ──✗  atlas/capabilities/     (clients only ever see Atlas, per ADR-002 -- unchanged)
atlas/_service.py     ──►  atlas/capabilities/*    (Atlas composes capabilities; capabilities never import Atlas)
atlas/capabilities/*  ──►  engine/*                (same repos/services each capability already used inside Atlas)
atlas/capabilities/*  ──✗  atlas/capabilities/*    (no capability imports another capability -- no cross-coupling)
atlas/capabilities/*  ──✗  presentation/*          (except PresentationCapability, which already depended on it via Atlas)
```

No capability introduces a new dependency that `Atlas` didn't already have. This is a **relocation** of existing `Atlas` method bodies, not new wiring.

### 3.3 Per-Capability Design

#### ProjectCapability

**Responsibilities:** Project lifecycle — creation (with workflow initialization as a side effect), loading, listing, archiving. Exactly the logic currently in `Atlas.create_project`, `load_project`, `list_projects`, `archive_project`.

**Public methods:**
```python
def create_project(self, command: CreateProjectCommand) -> ProjectResult
def load_project(self, command: LoadProjectCommand) -> ProjectResult
def list_projects(self, command: ListProjectsCommand) -> ProjectListResult
def archive_project(self, command: ArchiveProjectCommand) -> OperationResult
```

**Delegation:** `ProjectCreationService`, `ProjectLoadingService`, `ProjectRegistryService`, `ProjectLifecycleService` (unchanged, injected at construction), plus `WorkflowInitializationService` for the create-project side effect (`initialize_workflow(project.id)`). Owns the `_map_project_exception` translation (relocated verbatim from `Atlas`).

#### WorkflowCapability

**Responsibilities:** Workflow status and readiness reporting, stage transitions. Exactly the logic currently in `Atlas.get_workflow_status` and `Atlas.transition_stage`.

**Public methods:**
```python
def get_workflow_status(self, command: GetWorkflowStatusCommand) -> WorkflowStatusResult
def transition_stage(self, command: TransitionStageCommand) -> WorkflowStatusResult
```

**Delegation:** `WorkflowRepository`, `WorkflowTransitionService`, `WorkflowOrchestrationService.readiness_service`, `WorkflowOrchestrationService.knowledge_orchestration` (read-only, for `pending_knowledge_candidates`). Owns `_map_workflow_exception`.

#### WorkflowExecutionCapability

**Responsibilities:** AI stage execution and proposal review decisions. Exactly the logic currently in `Atlas.execute_stage`, `approve_proposal`, `reject_proposal`, including the pending-proposal cache.

**Public methods:**
```python
def execute_stage(self, command: ExecuteStageCommand) -> ProposalResult
def approve_proposal(self, command: ApproveProposalCommand) -> CommitResult
def reject_proposal(self, command: RejectProposalCommand) -> OperationResult
```

**Delegation:** `WorkflowRepository` (active-stage check), `WorkflowOrchestrationService.generate_proposal` / `process_review_decision`, `ProposalRepository`. Owns the `_pending_proposals: dict[UUID, tuple[UUID, AIProposal[Any]]]` cache (relocated from `Atlas.__init__`) and `_map_ai_exception` / `_map_workflow_exception`.

#### KnowledgeCapability

**Responsibilities:** Human review of knowledge candidates and the knowledge read model. Exactly the logic currently in `Atlas.review_knowledge_candidate` and `Atlas.get_knowledge_read_model`.

**Public methods:**
```python
def review_knowledge_candidate(self, command: ReviewKnowledgeCandidateCommand) -> OperationResult
def get_knowledge_read_model(self, project_id: UUID) -> KnowledgeReadModel
```

**Delegation:** `WorkflowOrchestrationService.process_knowledge_review`, `KnowledgeRepository`.

#### PresentationCapability

**Responsibilities:** All Phase 14 typed read models (project/workflow/research/diagnostics), composed views, and rendering. Exactly the logic currently in `Atlas.get_project_read_model` through `Atlas.render`.

**Public methods:**
```python
def get_project_read_model(self, project_id: UUID) -> ProjectReadModel
def get_workflow_read_model(self, project_id: UUID) -> WorkflowReadModel
def get_research_read_model(self, project_id: UUID) -> ResearchReadModel
def get_knowledge_read_model(self, project_id: UUID) -> KnowledgeReadModel
def get_diagnostics_read_model(self, project_id: UUID) -> DiagnosticsReadModel
def get_project_dashboard_view(self, project_id: UUID) -> ProjectDashboardView
def get_workflow_status_view(self, project_id: UUID) -> WorkflowStatusView
def get_research_summary_view(self, project_id: UUID) -> ResearchSummaryView
def get_knowledge_summary_view(self, project_id: UUID) -> KnowledgeSummaryView
def get_diagnostics_view(self, project_id: UUID) -> DiagnosticsView
def render(self, view: Any, renderer: str, contract: RenderContract | None = None) -> RenderResult
def _bind(self, platform_orchestration: PlatformOrchestrationService, renderer_registry: RendererRegistry) -> None
```

**Delegation:** `research_repo`, `planning_repo`, `architecture_repo`, `evaluation_repo`, `knowledge_repo`, `project_loading_service`, `workflow_repo` (all `| None`-typed exactly as today), plus `PlatformOrchestrationService` / `RendererRegistry` attached post-construction via `_bind` — **preserving the exact two-phase dance** documented in `docs/architecture/presentation-layer.md` §"Composition Root", only relocated from `Atlas._bind_presentation` to `PresentationCapability._bind`. `Atlas._bind_presentation` becomes a one-line forwarder: `self._presentation._bind(platform_orchestration, renderer_registry)`.

### 3.4 Ownership Matrix

| Concern | Owner (Phase 15) | Owner (Phase 1-14, for comparison) |
|---|---|---|
| Project lifecycle | `ProjectCapability` | `Atlas` methods directly |
| Workflow status/transitions | `WorkflowCapability` | `Atlas` methods directly |
| AI proposal generation + review | `WorkflowExecutionCapability` | `Atlas` methods directly |
| Knowledge review + read model | `KnowledgeCapability` | `Atlas` methods directly |
| Read models, views, rendering | `PresentationCapability` | `Atlas` methods directly |
| Composition / capability wiring | `Atlas.__init__` | N/A (methods were inline) |
| Envelope dispatch | `Atlas.handle()` | N/A (new) |
| Bootstrap / composition root | `atlas/_bootstrap.py` | Unchanged |

No responsibility overlap; no capability owns another capability's engine dependency.

### 3.5 Capability Responsibility Rule (Architectural Invariant)

This rule is locked for Phase 15 and is non-negotiable for any capability added in a future phase. It must be reproduced verbatim in `docs/decisions/adr-004-platform-capability-contract-layer.md` and `docs/architecture/platform-layer.md` (§10).

> **Capabilities are platform orchestration boundaries. They are not business-logic owners.**
>
> A capability **may**:
> - validate platform-level inputs (e.g. that a Command's referenced project matches the active workflow's project)
> - coordinate calls to existing Phase 1–14 services, in the same sequence `Atlas` used before Phase 15
> - translate internal engine exceptions into `ApplicationError` subclasses (relocated verbatim from `Atlas`)
> - map platform contracts (Command → Result, Result → envelope)
> - return platform DTOs (`Result` subclasses, read models, views)
>
> A capability **must not**:
> - implement business rules (invariants, lifecycle transitions, validation of domain state) — those remain exclusively in `engine/*` services
> - duplicate domain logic that already exists in an engine service
> - access persistence (repositories) for any purpose beyond what `Atlas` already did — no capability opens a new read/write path an engine service doesn't already expose
> - bypass an existing service to reach a repository or another engine internal directly
> - become an alternative engine layer — if a capability's method grows business logic, that logic has been misplaced and belongs in the relevant `engine/*` service instead
>
> Business logic remains exclusively inside existing Phase 1–14 services (`engine/project`, `engine/workflow`, `engine/knowledge`, `engine/ai`, etc.). Capabilities remain intentionally thin delegation layers — this is why §9.2's equivalence tests assert byte-identical `Result` output against the pre-Phase-15 `Atlas` methods: a capability that changed behavior would fail those tests immediately.

---

## 4. Atlas Facade Changes

`atlas/_service.py` keeps its exact public method signatures. Each becomes a one-line forward:

```python
def create_project(self, command: CreateProjectCommand) -> ProjectResult:
    """Initialize a new local engineering project."""
    return self._project.create_project(command)
```

`Atlas.__init__` constructs the five capabilities from `_AtlasServices` fields (unchanged dataclass — see §8) instead of assigning services directly to `self._*`:

```python
def __init__(self, services: _AtlasServices) -> None:
    self._project = ProjectCapability(...)
    self._workflow = WorkflowCapability(...)
    self._workflow_execution = WorkflowExecutionCapability(...)
    self._knowledge = KnowledgeCapability(...)
    self._presentation = PresentationCapability(...)
    self._dispatch = _build_dispatch_table(self)   # explicit literal dict, see §6.3
    self._platform_orchestration = None   # unchanged: set via _bind_presentation
    self._renderer_registry = None
```

`_require_presentation()` moves to `PresentationCapability` (it already only guards presentation state).

### 4.1 New: `Atlas.handle()`

```python
def handle(self, envelope: RequestEnvelope[Command]) -> ResponseEnvelope[Result]:
    """The single uniform doorway every out-of-process or protocol-driven
    client (MCP, REST, IDE, AI/agent) is expected to call through. In-process
    adapters (CLI today) may continue calling named methods directly."""
    handler = self._dispatch.get(type(envelope.command))
    if handler is None:
        error = ErrorEnvelope(
            code=PlatformErrorCode.UNKNOWN_ERROR,
            message=f"Unrecognized command type: {type(envelope.command).__name__}",
        )
        return ResponseEnvelope(request_id=envelope.request_id, error=error)
    try:
        result = handler(envelope.command)
        return ResponseEnvelope(request_id=envelope.request_id, result=result)
    except ApplicationError as exc:
        return ResponseEnvelope(
            request_id=envelope.request_id, error=to_error_envelope(exc)
        )
```

`_dispatch` is an explicit, literal `dict[type[Command], Callable[[Command], Result]]` built once in `__init__` — ten entries, one per existing command type. No reflection, no `getattr`-by-name magic, consistent with the codebase's existing "explicit registration, no dynamic discovery" rule (already used for `ExtractorRegistry` in Phase 13 and `RendererRegistry` in Phase 14).

### 4.2 Usage Policy — Named Methods vs. Envelope Dispatch (Architectural Invariant)

This policy is locked for Phase 15 and must be reproduced in `docs/decisions/adr-004-platform-capability-contract-layer.md` and `docs/architecture/platform-layer.md` (§10).

**Named methods** (`create_project`, `execute_stage`, `get_project_dashboard_view`, etc.) **remain permanently supported** for:

- the CLI adapter
- test suites (`tests/test_atlas/*`, `tests/support/*`)
- internal tooling
- any direct SDK consumer that is in-process with the `Atlas` instance

They are **not deprecated** — there is no scheduled removal, no `DeprecationWarning`, and no plan to make them thin shims scheduled for deletion. This resolves User Review Item 2 (§1) as: coexist permanently.

**`Atlas.handle(RequestEnvelope)` is the preferred entry point** for:

- MCP adapters
- REST adapters
- IDE integrations
- AI agents / autonomous callers
- any future out-of-process or protocol-driven adapter

These callers are "preferred" to use `.handle()`, not required by any runtime enforcement — `Atlas` does not reject named-method calls from any caller type. The distinction is architectural guidance for adapter authors, not a gate: out-of-process/protocol adapters *need* the envelope's `request_id`, `api_version`, and `adapter` identity for serialization, logging, tracing, and version negotiation, so `.handle()` is the only entry point that gives them that metadata. In-process callers have no such need.

This keeps exactly **one explicit protocol boundary** (`Atlas.handle()`) for external/protocol adapters while preserving full backward compatibility for everything already calling named methods today. No implementation change results from documenting this policy — both paths already exist as designed in §4.1.

---

## 5. Client Adapter Boundary Changes

### 5.1 CLI Retrofit (Minimal)

`clients/cli/application.py` gains exactly two additions:

```python
from atlas.adapters.protocol import AdapterContext, AdapterKind
from atlas.capabilities.base import CapabilityName

class CLIApplication:
    def __init__(self, ...) -> None:
        ...
        self._context = AdapterContext(kind=AdapterKind.CLI, name="atlas-cli", version=_VERSION)

    @property
    def context(self) -> AdapterContext:
        return self._context

    def negotiate(self, atlas_platform: Atlas) -> PlatformCapabilityManifest:
        # Static manifest in Phase 15 -- see §2.4.
        return PlatformCapabilityManifest(
            api_version=PLATFORM_API_VERSION,
            capabilities=(
                CapabilityName.PROJECT,
                CapabilityName.WORKFLOW,
                CapabilityName.WORKFLOW_EXECUTION,
                CapabilityName.KNOWLEDGE,
                CapabilityName.PRESENTATION,
            ),
        )
```

`CLIApplication._dispatch()` is **unchanged** — it keeps calling named `Atlas` methods directly. This proves the adapter boundary is real (CLI structurally satisfies `PlatformAdapter`, verified by an `isinstance` test, §9.4) without forcing a rewrite of the one adapter that already works. No import of `engine.*` is added; `clients/cli` still imports only from `atlas`.

### 5.2 MCP / IDE / REST / Desktop

Unchanged in this phase — still `__init__.py`-only stub packages. `docs/architecture/client-adapters.md` is updated (§10) to state explicitly that any adapter built against these stubs in a future phase must implement `PlatformAdapter` and is expected to call through `Atlas.handle()` (not named methods), since out-of-process/protocol adapters need the envelope's `request_id`/version/adapter-identity metadata for serialization, logging, and tracing — the CLI is the one exception because it is in-process.

---

## 6. Bootstrap Changes

### 6.1 What Does *Not* Change

`atlas/_bootstrap.py`'s construction sequence (sections 1–9 in the current file) is **untouched**. It still:

- Constructs all repositories and services in the same order.
- Constructs `Atlas(_AtlasServices(...))` the same way, with the same fields.
- Performs the same two-phase presentation bind (`PlatformOrchestrationService` → `RendererRegistry` → `atlas._bind_presentation(...)`).

### 6.2 What Changes

Nothing in `_bootstrap.py` itself. The only change is *inside* `Atlas.__init__` (§4), which now builds five capability objects from the same `_AtlasServices` fields instead of assigning them to instance attributes directly. `_AtlasServices` (the frozen dataclass) is **unchanged** — same fields, same optionality, same defaults. This keeps `tests/support/test_bootstrap.py`'s `create_test_platform` helper valid with zero modification.

### 6.3 Composition Root Invariant Preserved

- Bootstrap remains the only place that ever calls `Atlas(...)`.
- `Atlas.__init__` remains deterministic, explicit constructor injection — building `ProjectCapability(project_creation_service=..., ...)` etc. is still assignment, not a locator or registry lookup.
- The `_dispatch` table (§4.1) is built once, in `__init__`, from a literal dict — not a runtime-mutable registry, not reflection-based auto-discovery. It is added to `tests/support/test_bootstrap.py`'s existing "no service locator" static-source check (`test_atlas_class_has_no_service_locator`) as an explicit non-regression case: `"getattr(self, f\"" not in source` (guards against a future refactor turning `_dispatch` into stringly-typed dynamic lookup).

---

## 7. Atlas SDK / Public Surface Changes

**New public exports** (all additive; nothing existing is removed or renamed):

```python
# atlas/contracts/__init__.py
from atlas.contracts.envelope import RequestEnvelope, ResponseEnvelope
from atlas.contracts.errors import ErrorEnvelope, PlatformErrorCode
from atlas.contracts.version import PLATFORM_API_VERSION, SCHEMA_VERSION, is_compatible

# atlas/adapters/__init__.py
from atlas.adapters.protocol import (
    AdapterContext, AdapterKind, PlatformAdapter, PlatformCapabilityManifest,
)
```

`atlas/capabilities/` is **not** re-exported from `atlas/__init__.py` — it is an internal implementation detail of `Atlas`, exactly like `atlas/_bootstrap.py` today (module docstring states this explicitly, mirroring the existing `_bootstrap.py` header comment). `atlas/contracts/` and `atlas/adapters/` **are** part of the public SDK surface — adapter authors (future MCP/IDE implementers) need to import `RequestEnvelope`, `AdapterContext`, `PlatformAdapter`, etc.

`atlas/__init__.py`'s docstring ("Client adapters should import only from this package") is updated to note that `atlas.contracts` and `atlas.adapters` are the sub-modules adapters use for envelope/protocol types, while `atlas` itself remains the entry point for `create()`, `Atlas`, and `BootstrapError`.

---

## 8. Package Structure (Full Diff View)

```
atlas/
├── __init__.py                     [doc update only]
├── _bootstrap.py                   [UNCHANGED]
├── _service.py                     [modified: method bodies -> one-line forwards; __init__ builds capabilities + dispatch table; new handle()]
├── commands.py                     [UNCHANGED]
├── results.py                      [UNCHANGED]
├── exceptions.py                   [UNCHANGED]
├── types.py                        [UNCHANGED]
├── capabilities/                   [NEW — internal]
│   ├── __init__.py
│   ├── base.py                     # CapabilityName enum
│   ├── project_capability.py
│   ├── workflow_capability.py
│   ├── workflow_execution_capability.py
│   ├── knowledge_capability.py
│   └── presentation_capability.py
├── contracts/                      [NEW — public]
│   ├── __init__.py
│   ├── envelope.py
│   ├── errors.py
│   └── version.py
└── adapters/                       [NEW — public]
    ├── __init__.py
    └── protocol.py

clients/cli/application.py          [modified: + AdapterContext, + context property, + negotiate()]
```

No changes anywhere under `engine/`, `presentation/`, `interfaces/`, `shared/`, `clients/common/`, `clients/mcp/`, `clients/ide/`, `clients/rest/`, `clients/desktop/`.

---

## 9. Testing Strategy

### 9.1 Test Package Structure

```
tests/test_atlas/
├── test_capabilities.py         # behavior-equivalence: named method == capability method, for all 5 capabilities
├── test_platform_handle.py      # Atlas.handle() equivalence for all 10 command types + unknown-command path
tests/contracts/
├── test_envelope.py             # round-trip serialization; frozen; exactly-one-of(result, error)
├── test_errors.py               # completeness (every ApplicationError subclass mapped); retryable flags
└── test_version.py              # is_compatible() matrix (same major / different major / same version)
tests/adapters/
└── test_protocol.py             # CLIApplication isinstance-satisfies PlatformAdapter; manifest shape
tests/architecture/
└── test_platform_boundaries.py  # AST-based import-direction checks (see §9.3)
tests/support/
└── test_bootstrap.py            # [existing file, extended] no-service-locator check covers _dispatch
```

### 9.2 Unit Tests

| Target | Cases |
|---|---|
| `ProjectCapability` / `WorkflowCapability` / `WorkflowExecutionCapability` / `KnowledgeCapability` / `PresentationCapability` | Each public method produces byte-identical `Result` to today's `Atlas` method, given identical fixtures (regression harness reused from existing `tests/test_atlas/*`) |
| `RequestEnvelope` / `ResponseEnvelope` | Serialize/deserialize round-trip; frozen (mutation raises); exactly one of `result`/`error` populated (validator rejects both-set and neither-set) |
| `PlatformErrorCode` / `to_error_envelope` | Every `ApplicationError` subclass maps to a distinct, non-`UNKNOWN_ERROR` code; `AIProviderError` → `retryable=True`; all others `retryable=False` |
| `is_compatible` | `"1.0.0"` vs `"1.0.0"` → True; `"1.2.7"` vs `"1.0.0"` → True; `"2.0.0"` vs `"1.0.0"` → False |
| `PlatformAdapter` protocol | `CLIApplication` instance passes `isinstance(app, PlatformAdapter)`; `negotiate()` returns all 5 capability names and current `PLATFORM_API_VERSION` |
| `Atlas.handle()` | Dispatch table has exactly 10 entries (one per existing Command subclass); unrecognized command type → `ResponseEnvelope.error.code == UNKNOWN_ERROR`; `ApplicationError` raised inside a capability is caught and mapped, never propagates out of `handle()` |

### 9.3 Boundary / Architecture Tests

AST-based static checks in `tests/architecture/test_platform_boundaries.py` (same technique as `tests/architecture/test_presentation_boundaries.py`):

- `atlas/capabilities/*.py` contain no `import engine` statements outside the exact repo/service types each capability already depended on via `Atlas` (i.e., no *new* engine surface area is reachable).
- `atlas/capabilities/*.py` never import from `atlas.capabilities` (no cross-capability imports).
- `atlas/contracts/*.py` and `atlas/adapters/*.py` never import from `engine.*` or `presentation.*` (pure DTO/protocol modules).
- `clients/cli/application.py` still imports nothing from `engine.*` (pre-existing rule, re-verified after the retrofit).
- `atlas/capabilities/*.py` are never imported from `clients/*` (capabilities are `Atlas`-internal only).

### 9.4 Completeness / Regression Tests

- `test_errors.py::test_all_application_errors_mapped` — iterates `ApplicationError.__subclasses__()` (mirroring the pattern already used in `tests/support/test_platform_bootstrap.py` for static source checks) and asserts every concrete subclass is a key in `_ERROR_CODE_MAP`.
- `test_bootstrap.py::test_atlas_class_has_no_service_locator` — extended with the `_dispatch` non-regression assertion (§6.3).
- `test_platform_handle.py::test_handle_matches_named_method_for_every_command` — parametrized over all 9 existing Command types, asserting `atlas.handle(RequestEnvelope(adapter=..., command=cmd)).result == getattr(atlas, method_name)(cmd)` for identical fixture state.

### 9.5 Coverage Targets

| Area | Target |
|---|---|
| `atlas/capabilities/` | ≥ 95% line coverage (thin delegation code; should be nearly total) |
| `atlas/contracts/` | 100% branch coverage (small, pure, high-value modules) |
| `atlas/adapters/` | 100% branch coverage |
| `_dispatch` table / `handle()` | 100% — every command type exercised, plus the unknown-command path |
| Overall `atlas/` | No regression vs. Phase 14 baseline |

---

## 10. Documentation Changes

### 10.1 New Documents

| Document | Content |
|---|---|
| `docs/architecture/platform-layer.md` | Full description of the capability layer, contract layer, adapter boundary, versioning policy, and how they compose with the existing Application Platform Layer (ADR-002) and Presentation Layer (Phase 14). **Must reproduce verbatim:** the Capability Responsibility Rule (§3.5) and the Named-Methods-vs-Envelope usage policy (§4.2), and state the `UNKNOWN_ERROR` architectural intent (§2.2) |
| `docs/decisions/adr-004-platform-capability-contract-layer.md` | Locks Phase 15 decisions: capability decomposition (including the `WorkflowExecutionCapability` naming and its narrower AI-proposal-generation/approval/rejection scope, §3.3), the strongly-typed `CapabilityName` enum (§3.0), envelope contract, error-code mapping, `UNKNOWN_ERROR` fallback-only intent, versioning policy, adapter protocol, and the Capability Responsibility Rule (§3.5) and handle() usage policy (§4.2) as locked invariants |
| `docs/diagrams/platform-request-dispatch.md` | Sequence diagram: Adapter → `RequestEnvelope` → `Atlas.handle()` → dispatch table → Capability (`ProjectCapability` / `WorkflowCapability` / `WorkflowExecutionCapability` / `KnowledgeCapability` / `PresentationCapability`) → existing engine services → `ResponseEnvelope` (and the CLI's alternate named-method path) |

### 10.2 Updated Documents

| Document | Changes |
|---|---|
| `docs/architecture/application-platform.md` | Cross-reference the new Platform Layer doc; note that "capability-based authorization scopes" (existing Future Extensions bullet) now has a concrete seam (`PlatformCapabilityManifest`, typed via `CapabilityName`) though authorization itself remains unimplemented |
| `docs/architecture/client-adapters.md` | Add `PlatformAdapter` protocol, `AdapterContext`, capability negotiation (manifest values drawn from `CapabilityName`); state the CLI-is-in-process-exception explicitly; state the named-methods-remain-permanent / `Atlas.handle()`-preferred-for-external-adapters policy (§4.2) verbatim; note future MCP/IDE/REST/Desktop adapters are expected to call `Atlas.handle()` |
| `docs/glossary.md` | Add: Platform Capability, Capability Layer, Capability Responsibility Rule, `CapabilityName`, `WorkflowExecutionCapability`, Request Envelope, Response Envelope, Error Envelope, `UNKNOWN_ERROR` (fallback-only), Platform API Version, Adapter Context, Capability Manifest |
| `docs/diagrams/application-platform.md` | Add the `handle()` path alongside the existing named-method path; label both per the §4.2 usage policy (permanent vs. preferred-for-external) |
| `docs/diagrams/client-adapter-layer.md` | Add adapter negotiation step; label capabilities using `CapabilityName` values, not raw strings |
| `docs/diagrams/request-lifecycle.md` | Add envelope variant of the request lifecycle |
| `README.md` | Add `atlas/capabilities/`, `atlas/contracts/`, `atlas/adapters/` under the `atlas/` package-structure bullet |
| `CHANGELOG.md` | Phase 15 entry |
| `PROGRESS.md` | Phase 15 tracking |

### 10.3 Blueprint Updates (informational)

| Document | Changes |
|---|---|
| `Blueprint/09-service-contracts.md` | Add `PlatformAdapter` protocol and envelope contracts alongside existing service contracts |
| `Blueprint/05-system-architecture.md` | Cross-reference the new internal seam (no structural change to the diagram's boundary — it already shows `atlas/` as the single boundary clients cross) |

---

## 11. Verification Plan

### 11.1 Automated Verification

```bash
uv run pytest
uv run mypy .
uv run ruff check .
uv run ruff format .
```

### 11.2 Architectural Verification

| Check | Expected |
|---|---|
| No engine changes | `git diff --stat` shows zero changes under `engine/` |
| No presentation changes | `git diff --stat` shows zero changes under `presentation/` |
| Command/Result shapes unchanged | `atlas/commands.py` and `atlas/results.py` byte-identical to Phase 14 baseline |
| Named methods behave identically | Full existing `tests/test_atlas/*` suite passes unmodified against the refactored `Atlas` |
| One dispatch table, explicit | `_dispatch` is a literal dict built in `__init__`; no `getattr(self, name)` dynamic lookup anywhere in `atlas/_service.py` |
| Error contract completeness | Every `ApplicationError` subclass has a `PlatformErrorCode` |
| No cross-capability coupling | AST check: no `atlas.capabilities` imports inside `atlas/capabilities/*.py` |
| No new client-visible engine surface | `clients/cli/application.py` import set unchanged except for `atlas.adapters.protocol` |
| Composition root unchanged | `atlas/_bootstrap.py` diff is empty |
| Bootstrap remains sole constructor | `Atlas(...)` called only from `atlas/_bootstrap.py` and `tests/support/test_bootstrap.py` |

### 11.3 Manual Smoke Tests

1. **Named-method path (unchanged):** `atlas.create_project(CreateProjectCommand(...))` returns the same `ProjectResult` shape as before the refactor.
2. **Envelope path (new):** Build a `RequestEnvelope(adapter=AdapterContext(kind=AdapterKind.AI, name="test-agent", version="0.1.0"), command=CreateProjectCommand(...))`, call `atlas.handle(envelope)`, confirm `ResponseEnvelope.result` matches the named-method result and `ResponseEnvelope.request_id == envelope.request_id`.
3. **Error path:** `atlas.handle(RequestEnvelope(..., command=LoadProjectCommand(project_id=<nonexistent>)))` → `ResponseEnvelope.error.code == PlatformErrorCode.PROJECT_NOT_FOUND`, `result is None`.
4. **Adapter conformance:** `isinstance(CLIApplication(), PlatformAdapter)` → `True`; `CLIApplication().negotiate(atlas)` → manifest lists all 5 capability names.
5. **Version compatibility:** `is_compatible("1.4.2")` → `True`; `is_compatible("2.0.0")` → `False`.
6. **CLI regression:** `atlas <command>` end-to-end still works exactly as before (CLI never switched to `.handle()`).

---

## Implementation Sequence

| Sprint | Deliverables |
|---|---|
| **S1** | `atlas/contracts/` (envelope, errors, version) + unit tests |
| **S2** | `atlas/adapters/` (protocol, context, manifest) + unit tests |
| **S3** | `atlas/capabilities/` — five capability classes, behavior-equivalence tests against current `Atlas` |
| **S4** | Refactor `atlas/_service.py` to compose capabilities + add `handle()` + dispatch table |
| **S5** | CLI retrofit (`AdapterContext`, `context`, `negotiate()`) + adapter-conformance test |
| **S6** | Boundary/architecture tests, coverage pass, documentation (new + updated docs) |

---

## 12. Task Breakdown

Verified against the live codebase graph (`codebase-memory-mcp`, project `Users-sahilmangla-atlas`, 2791 nodes / 10776 edges) before being written — every method signature, field name, and `ApplicationError` subclass referenced below was cross-checked against the indexed source, not assumed. `atlas/exceptions.py` has exactly 11 concrete `ApplicationError` subclasses today (`ProjectNotFoundError`, `ProjectAlreadyExistsError`, `InvalidProjectError`, `ProjectLifecycleError`, `WorkflowNotReadyError`, `InvalidTransitionError`, `StageExecutionError`, `ProposalValidationError`, `ContextAssemblyError`, `AIProviderError`, `BootstrapError`) — this fixes `_ERROR_CODE_MAP`'s size at 11 entries for §2.2 and the completeness test in §9.4.

Waves below may run in parallel within a wave; each wave depends on the prior wave's tasks completing.

### Wave 1 — Contracts (independent of everything else)

**T1.1 — `atlas/contracts/version.py`**
- `read_first`: none (new file, no prior art to conform to beyond §2.3 of this plan)
- `action`: Create `PLATFORM_API_VERSION = "1.0.0"`, `SCHEMA_VERSION = 1`, `is_compatible(client_api_version: str) -> bool` exactly as specified in §2.3.
- `acceptance_criteria`: `is_compatible("1.0.0")`, `is_compatible("1.4.2")` → `True`; `is_compatible("2.0.0")` → `False`; module has zero imports from `engine.*` or `presentation.*`.

**T1.2 — `atlas/capabilities/base.py` (created early — contracts and adapters both depend on `CapabilityName`)**
- `read_first`: none
- `action`: Create `CapabilityName` `StrEnum` with exactly 5 members: `PROJECT`, `WORKFLOW`, `WORKFLOW_EXECUTION`, `KNOWLEDGE`, `PRESENTATION` (§3.0). No other content in this file yet — the 5 capability classes land in Wave 3.
- `acceptance_criteria`: `list(CapabilityName)` has length 5; `CapabilityName.WORKFLOW_EXECUTION.value == "workflow_execution"`.

**T1.3 — `atlas/adapters/protocol.py`**
- `read_first`: `atlas/capabilities/base.py` (T1.2, for `CapabilityName`)
- `action`: Create `AdapterKind` (`CLI`, `IDE`, `MCP`, `AI`, `REST`, `DESKTOP`), `AdapterContext` (frozen Pydantic model: `kind`, `name`, `version`), `PlatformCapabilityManifest` (frozen, `api_version: str`, `capabilities: tuple[CapabilityName, ...]`), `PlatformAdapter` (`@runtime_checkable` `Protocol` with `context` property and `negotiate(atlas) -> PlatformCapabilityManifest`) exactly as specified in §2.4.
- `acceptance_criteria`: `PlatformCapabilityManifest(api_version="1.0.0", capabilities=(CapabilityName.PROJECT,))` constructs and is frozen (mutation raises `ValidationError`); `AdapterContext` frozen the same way; `isinstance(x, PlatformAdapter)` returns `False` for an arbitrary object lacking `context`/`negotiate`.

**T1.4 — `atlas/contracts/errors.py`**
- `read_first`: `atlas/exceptions.py` (all 11 concrete subclasses + `ApplicationError` base)
- `action`: Create `PlatformErrorCode` (`StrEnum`, 12 members: 11 mapped codes + `UNKNOWN_ERROR`), `ErrorEnvelope` (frozen: `code`, `message`, `retryable: bool = False`), the literal `_ERROR_CODE_MAP: dict[type[ApplicationError], PlatformErrorCode]` with all 11 entries, `_RETRYABLE: frozenset[type[ApplicationError]] = frozenset({AIProviderError})`, and `to_error_envelope(exc: ApplicationError) -> ErrorEnvelope` exactly as specified in §2.2. Include the `UNKNOWN_ERROR` architectural-intent docstring from §2.2 verbatim as the module or enum-member docstring.
- `acceptance_criteria`: `to_error_envelope(ProjectNotFoundError("x")).code == PlatformErrorCode.PROJECT_NOT_FOUND`; `to_error_envelope(AIProviderError("x")).retryable is True`; every other mapped type → `retryable is False`; `len(_ERROR_CODE_MAP) == 11`.

**T1.5 — `atlas/contracts/envelope.py`**
- `read_first`: `atlas/commands.py` (`Command` base), `atlas/results.py` (`Result` base), `atlas/adapters/protocol.py` (T1.3, for `AdapterContext`), `atlas/contracts/errors.py` (T1.4, for `ErrorEnvelope`)
- `action`: Create generic `RequestEnvelope[TCommand]` (frozen: `api_version`, `request_id: UUID = Field(default_factory=uuid4)`, `adapter: AdapterContext`, `command: TCommand`) and `ResponseEnvelope[TResult]` (frozen: `api_version`, `request_id`, `result: TResult | None`, `error: ErrorEnvelope | None`) exactly as specified in §2.1, plus a model validator enforcing exactly one of `result`/`error` is set.
- `acceptance_criteria`: `ResponseEnvelope(request_id=uuid4(), result=None, error=None)` raises a validation error; `ResponseEnvelope(request_id=uuid4(), result=SomeResult(...), error=None)` constructs; same for `error`-only; both `RequestEnvelope`/`ResponseEnvelope` reject field mutation after construction.

**T1.6 — `atlas/contracts/__init__.py` / `atlas/adapters/__init__.py`**
- `read_first`: `atlas/__init__.py` (existing export-surface convention)
- `action`: Export `RequestEnvelope`, `ResponseEnvelope` from `atlas.contracts.envelope`; `ErrorEnvelope`, `PlatformErrorCode` from `atlas.contracts.errors`; `PLATFORM_API_VERSION`, `SCHEMA_VERSION`, `is_compatible` from `atlas.contracts.version` — in `atlas/contracts/__init__.py`. Export `AdapterContext`, `AdapterKind`, `PlatformAdapter`, `PlatformCapabilityManifest` from `atlas.adapters.protocol` in `atlas/adapters/__init__.py`. Update `atlas/__init__.py`'s module docstring per §7 (mention `atlas.contracts` / `atlas.adapters` as adapter-facing sub-modules).
- `acceptance_criteria`: `from atlas.contracts import RequestEnvelope, ResponseEnvelope, ErrorEnvelope, PlatformErrorCode, PLATFORM_API_VERSION` succeeds; `from atlas.adapters import PlatformAdapter, AdapterContext, AdapterKind, PlatformCapabilityManifest` succeeds; `atlas/__init__.py`'s `__all__` is unchanged (`["Atlas", "create"]` — contracts/adapters are imported as sub-modules, not re-exported at top level).

### Wave 2 — Test scaffolding for Wave 1 (parallel with Wave 1 completion, blocks nothing downstream)

**T2.1 — `tests/contracts/test_version.py`, `test_errors.py`, `test_envelope.py`**
- `read_first`: T1.1, T1.4, T1.5 outputs
- `action`: Implement the unit tests specified in §9.2 for these three modules, plus `test_errors.py::test_all_application_errors_mapped` from §9.4 (iterate `ApplicationError.__subclasses__()`, assert each is a key in `_ERROR_CODE_MAP`).
- `acceptance_criteria`: `uv run pytest tests/contracts/ -v` — all pass; `test_all_application_errors_mapped` fails if a subclass is temporarily removed from `_ERROR_CODE_MAP` in a scratch edit (sanity-check the test actually asserts, don't just check it imports).

**T2.2 — `tests/adapters/test_protocol.py`**
- `read_first`: T1.3 output
- `action`: Test `PlatformCapabilityManifest` construction/immutability and `AdapterContext` construction/immutability per §9.2 (CLI-specific isinstance check happens in Wave 5, T5.2, once `CLIApplication` is retrofitted).
- `acceptance_criteria`: `uv run pytest tests/adapters/ -v` passes.

### Wave 3 — Capability Layer (depends on Wave 1 for contract types used in signatures; does not depend on Wave 1's tests)

**T3.1 — `atlas/capabilities/project_capability.py` (`ProjectCapability`)**
- `read_first`: `atlas/_service.py` (current `Atlas.create_project`, `load_project`, `list_projects`, `archive_project`, `_map_project_exception` — copy logic verbatim, do not reinterpret), `atlas/commands.py`, `atlas/results.py`, `atlas/exceptions.py`, `engine/project/services.py` (`ProjectCreationService`, `ProjectLoadingService`, `ProjectRegistryService`, `ProjectLifecycleService`), `engine/workflow/services.py` (`WorkflowInitializationService`)
- `action`: Construct `ProjectCapability` with the exact constructor-injected services listed in §3.3, exposing the 4 public methods listed there with identical bodies to today's `Atlas` methods (byte-for-byte logic, only `self._project_creation_service` etc. renamed to match the capability's own attribute names). Relocate `_map_project_exception` as a private method on this class.
- `acceptance_criteria`: `tests/test_atlas/test_capabilities.py::test_project_capability_matches_atlas_today` — construct `ProjectCapability` with the same fixture services used in `tests/test_atlas/test_project_commands.py`, call each of the 4 methods, assert identical `Result` to calling the corresponding pre-refactor `Atlas` method (the plan does not require deleting the old `Atlas` code until T4.1, so this test can run both side by side during this wave).

**T3.2 — `atlas/capabilities/workflow_capability.py` (`WorkflowCapability`)**
- `read_first`: `atlas/_service.py` (`get_workflow_status`, `transition_stage`, `_map_workflow_exception`), `engine/workflow/repository.py`, `engine/workflow/services.py` (`WorkflowTransitionService`), `engine/workflow/orchestration.py` (`WorkflowOrchestrationService.readiness_service`, `.knowledge_orchestration`)
- `action`: Per §3.3 — 2 public methods, delegation exactly as listed, relocate `_map_workflow_exception`.
- `acceptance_criteria`: Equivalence test against `tests/test_atlas/test_workflow_commands.py` fixtures, same pattern as T3.1.

**T3.3 — `atlas/capabilities/workflow_execution_capability.py` (`WorkflowExecutionCapability`)**
- `read_first`: `atlas/_service.py` (`execute_stage`, `approve_proposal`, `reject_proposal`, `_map_ai_exception`, `_map_workflow_exception`, the `_pending_proposals` cache in `__init__`), `engine/workflow/orchestration.py` (`WorkflowOrchestrationService.generate_proposal`, `.process_review_decision`), `engine/ai/repository.py` (`ProposalRepository`)
- `action`: Per §3.3 — this capability's name and scope is intentionally narrower than a generic "execution" concept: it owns exactly AI proposal generation (`execute_stage`) and the two proposal review decisions (`approve_proposal`, `reject_proposal`), nothing else. Relocate the `_pending_proposals: dict[UUID, tuple[UUID, AIProposal[Any]]]` cache into this class's `__init__`, plus both exception-mapping helpers.
- `acceptance_criteria`: Equivalence test against `tests/test_atlas/test_execution_commands.py` fixtures. Class name in source is exactly `WorkflowExecutionCapability` (grep-checked by T6.x boundary test, not just this task).

**T3.4 — `atlas/capabilities/knowledge_capability.py` (`KnowledgeCapability`)**
- `read_first`: `atlas/_service.py` (`review_knowledge_candidate`, `get_knowledge_read_model`), `engine/workflow/orchestration.py` (`.process_knowledge_review`), `engine/knowledge/repository.py`
- `action`: Per §3.3 — 2 public methods.
- `acceptance_criteria`: Equivalence test against `tests/test_atlas/test_knowledge_commands.py` fixtures.

**T3.5 — `atlas/capabilities/presentation_capability.py` (`PresentationCapability`)**
- `read_first`: `atlas/_service.py` (`get_project_read_model` through `render`, plus `_bind_presentation`/`_require_presentation`), `docs/architecture/presentation-layer.md` (the two-phase bind contract — must be preserved exactly), `presentation/orchestration/platform.py`, `presentation/renderers/registry.py`
- `action`: Per §3.3 — 11 public methods plus a `_bind(platform_orchestration, renderer_registry)` method replicating the exact two-phase construction contract documented in `presentation-layer.md`. This is the one capability requiring the deferred-attach pattern; the other four are fully constructed in one step.
- `acceptance_criteria`: `tests/support/test_platform_bootstrap.py`'s existing 6 tests pass unmodified once `Atlas._bind_presentation` forwards to `PresentationCapability._bind` (verifies the two-phase dance survived relocation intact).

**T3.6 — `atlas/capabilities/__init__.py`**
- `read_first`: T3.1–T3.5 outputs
- `action`: Export exactly the 5 capability classes, nothing else (per §7 — this package is Atlas-internal).
- `acceptance_criteria`: `tests/architecture/test_platform_boundaries.py::test_capabilities_not_imported_by_clients` (Wave 6) can rely on this being the only public surface.

### Wave 4 — Atlas Facade Refactor (depends on Wave 3 fully complete)

**T4.1 — Refactor `atlas/_service.py`**
- `read_first`: full current `atlas/_service.py` (all methods, `_AtlasServices` dataclass), all 5 capability classes (Wave 3), `atlas/contracts/envelope.py`, `atlas/contracts/errors.py` (T1.4/T1.5)
- `action`: Rewrite `Atlas.__init__` to construct the 5 capabilities from `_AtlasServices` fields (§4), replace every existing public method body with a one-line forward to its capability (§4), add the `_dispatch` literal dict (10 entries — one per `Command` subclass in `atlas/commands.py`) and the new `handle()` method (§4.1) exactly as specified. `_AtlasServices` dataclass itself is **not modified** — same fields, same optionality.
- `acceptance_criteria`: Full existing `tests/test_atlas/*` suite passes unmodified (zero test file edits) against the refactored `Atlas` — this is the hard regression gate. `_dispatch` has exactly 10 entries. No `getattr(self,` dynamic dispatch anywhere in the file (grep-checked).

**T4.2 — `tests/test_atlas/test_platform_handle.py`**
- `read_first`: T4.1 output, `atlas/commands.py` (all 10 Command types)
- `action`: Parametrized test per §9.2/§9.4 — for each of the 10 Command types, build a `RequestEnvelope`, call `atlas.handle(...)`, assert `result` equals calling the named method directly on identical fixture state. Add the unknown-command-type test and the `ApplicationError`-is-caught-and-mapped test.
- `acceptance_criteria`: `uv run pytest tests/test_atlas/test_platform_handle.py -v` — all pass, 10 command types + 2 edge cases covered.

**T4.3 — Extend `tests/support/test_bootstrap.py`**
- `read_first`: `tests/support/test_bootstrap.py::test_atlas_class_has_no_service_locator`
- `action`: Add the `_dispatch` non-regression assertion described in §6.3 (`"getattr(self, f\"" not in source`).
- `acceptance_criteria`: Test passes against T4.1's implementation; fails if `_dispatch` is hypothetically rewritten to use dynamic `getattr`-by-name (sanity-checked with a scratch edit, then reverted).

### Wave 5 — CLI Retrofit (depends on Wave 4)

**T5.1 — Update `clients/cli/application.py`**
- `read_first`: current `clients/cli/application.py` in full (do not touch `_dispatch()` — it must remain calling named `Atlas` methods, per §5.1's explicit non-goal), `atlas/adapters/protocol.py`, `atlas/capabilities/base.py` (`CapabilityName`)
- `action`: Add the `AdapterContext` construction, `context` property, and `negotiate()` method exactly as specified in §5.1 (with `capabilities` built from `CapabilityName` enum members, not raw strings). No change to `CLIApplication._dispatch()`, `run()`, or `main()`.
- `acceptance_criteria`: `clients/cli/application.py`'s import set adds only `atlas.adapters.protocol` and `atlas.capabilities.base` — no `engine.*` import introduced. `CLIApplication().negotiate(atlas_instance).capabilities == (CapabilityName.PROJECT, CapabilityName.WORKFLOW, CapabilityName.WORKFLOW_EXECUTION, CapabilityName.KNOWLEDGE, CapabilityName.PRESENTATION)`.

**T5.2 — `tests/adapters/test_protocol.py` (CLI conformance case)**
- `read_first`: T5.1 output
- `action`: Add `isinstance(CLIApplication(...), PlatformAdapter) is True` (runtime-checkable Protocol check) and the manifest-shape assertion from §11.3 item 4.
- `acceptance_criteria`: Test passes; fails if `context` property or `negotiate()` is temporarily removed (sanity-checked).

### Wave 6 — Boundary Tests, Coverage, Documentation (depends on Waves 1–5)

**T6.1 — `tests/architecture/test_platform_boundaries.py`**
- `read_first`: `tests/architecture/test_presentation_boundaries.py` (existing AST-based pattern to reuse)
- `action`: Implement all 5 checks listed in §9.3.
- `acceptance_criteria`: All 5 pass against the Wave 1–5 output.

**T6.2 — Full verification pass**
- `read_first`: §11 of this plan (Verification Plan)
- `action`: Run `uv run pytest`, `uv run mypy .`, `uv run ruff check .`, `uv run ruff format .`; walk every row of the §11.2 architectural-verification table.
- `acceptance_criteria`: All commands exit 0; every §11.2 row confirmed true; `git diff --stat` shows zero changes under `engine/` and `presentation/`.

**T6.3 — Documentation**
- `read_first`: §10 of this plan (full documentation change list, including the verbatim-reproduction requirements for the Capability Responsibility Rule §3.5, the handle() usage policy §4.2, and the `UNKNOWN_ERROR` intent §2.2)
- `action`: Write `docs/architecture/platform-layer.md`, `docs/decisions/adr-004-platform-capability-contract-layer.md`, `docs/diagrams/platform-request-dispatch.md`; update `docs/architecture/application-platform.md`, `docs/architecture/client-adapters.md`, `docs/glossary.md`, `docs/diagrams/application-platform.md`, `docs/diagrams/client-adapter-layer.md`, `docs/diagrams/request-lifecycle.md`, `README.md`, `CHANGELOG.md`, `PROGRESS.md` per §10.1/§10.2.
- `acceptance_criteria`: Every file listed in §10.1/§10.2 exists/is updated; the three locked invariants (§3.5, §4.2, §2.2's `UNKNOWN_ERROR` note) appear verbatim (or near-verbatim, same substantive content) in both `platform-layer.md` and ADR-004.

---

## Appendix A: Integration Points

| File | Change |
|---|---|
| `atlas/contracts/envelope.py` | **New** — `RequestEnvelope`, `ResponseEnvelope` |
| `atlas/contracts/errors.py` | **New** — `PlatformErrorCode`, `ErrorEnvelope`, `to_error_envelope`, `_ERROR_CODE_MAP` |
| `atlas/contracts/version.py` | **New** — `PLATFORM_API_VERSION`, `SCHEMA_VERSION`, `is_compatible` |
| `atlas/adapters/protocol.py` | **New** — `AdapterKind`, `AdapterContext`, `PlatformCapabilityManifest`, `PlatformAdapter` |
| `atlas/capabilities/*.py` | **New package** — five capability classes |
| `atlas/_service.py` | Method bodies → forwards; `__init__` builds capabilities + `_dispatch`; new `handle()` |
| `atlas/_bootstrap.py` | **Unchanged** |
| `atlas/__init__.py` | Docstring update only |
| `clients/cli/application.py` | `+AdapterContext`, `+context` property, `+negotiate()` |
| `tests/test_atlas/test_capabilities.py` | **New** |
| `tests/test_atlas/test_platform_handle.py` | **New** |
| `tests/contracts/` | **New package** |
| `tests/adapters/` | **New package** |
| `tests/architecture/test_platform_boundaries.py` | **New** |
| `tests/support/test_bootstrap.py` | Extended (one new assertion) |

## Appendix B: Explicit Non-Goals

- Any change to `engine/*` subsystem boundaries, services, or persistence.
- Any change to `presentation/*` internals or the Phase 14 two-phase bind sequence's shape.
- Building real MCP, IDE, REST, or Desktop client adapters.
- Capability-based authorization / scoping enforcement (seam only).
- Event streams / subscriptions.
- Migrating the CLI's dispatch loop off named methods.
- Deprecating or removing any existing `Atlas` named method.
- Changing `Command` / `Result` DTO shapes.

---

**End of Phase 15 Implementation Plan**
