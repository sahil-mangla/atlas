# Phase 14: Presentation Layer

## Purpose
This document describes the `presentation/` package: the upper presentation layer that composes typed, immutable views from the Atlas facade's read-model API and renders them to concrete output formats (JSON, Markdown, CLI text).

## Responsibilities
- Define immutable presentation Components, Views, and typed Read Models.
- Aggregate Atlas read models into complete Views via Collectors.
- Orchestrate collector selection via `PlatformOrchestrationService`.
- Render immutable Views into `RenderResult` via format-specific Renderers.

## Non-Responsibilities
- Presentation is not an engine subsystem and never modifies engineering state.
- Presentation never accesses repositories, persistence, or the filesystem directly.
- Renderers never compute business meaning; they format only.

---

## Dependency Direction

```
Platform / Clients
  |
  v
Atlas Facade
  |
  v
PlatformOrchestrationService
  |
  v
Collectors
  |
  v
Typed Atlas Read Models
  |
  v
Existing Phase 1-13 services
```

There are no reverse dependencies. Presentation modules never import `engine.*`, repositories, persistence, or the filesystem. This is enforced by a static AST-based test suite: `tests/architecture/test_presentation_boundaries.py`.

## Engine Isolation

`presentation/` never imports `engine.ai`, `engine.workflow`, repositories, persistence, filesystem, or database modules. It communicates exclusively through the Atlas public read-model API:

- `Atlas.get_project_read_model(project_id) -> ProjectReadModel`
- `Atlas.get_workflow_read_model(project_id) -> WorkflowReadModel`
- `Atlas.get_research_read_model(project_id) -> ResearchReadModel`
- `Atlas.get_knowledge_read_model(project_id) -> KnowledgeReadModel`
- `Atlas.get_diagnostics_read_model(project_id) -> DiagnosticsReadModel`

Each read model is an immutable Pydantic DTO (`presentation/read_models/models.py`) sourced from existing Phase 1-13 services and repositories inside `atlas/_service.py`. No engine entity or repository object crosses this boundary -- only plain typed data.

## Read Models

`presentation/read_models/models.py` defines the five read models above. They are `ConfigDict(frozen=True)` Pydantic models with tuple-typed collections. Atlas is their sole producer; collectors are their sole consumer.

## Collectors

`presentation/collectors/collectors.py` defines one Collector per View kind:

- `ProjectDashboardCollector`
- `WorkflowStatusCollector`
- `ResearchSummaryCollector`
- `KnowledgeSummaryCollector`
- `DiagnosticsCollector`

Each collector's constructor takes an `Atlas` instance (typed under `TYPE_CHECKING` via the public `atlas` package to avoid a runtime import cycle -- see "Import Cycle" below). Each `collect(project_id)` method calls one or more `get_*_read_model` methods on Atlas, aggregates them, and returns a fully-composed, immutable View. Collectors never render, never call repositories or engine services directly, never perform AI work, and never mutate engineering state.

## Views

`presentation/views/models.py` defines five frozen, tuple-based Pydantic Views, joined into a discriminated union `PresentationView` on the `kind` field:

- `ProjectDashboardView`
- `WorkflowStatusView`
- `ResearchSummaryView`
- `KnowledgeSummaryView`
- `DiagnosticsView`

Views are deeply immutable (frozen models composed of frozen Components and tuples, never lists), renderer-independent, and contain no business logic or engine models.

## Components

`presentation/components/models.py` defines three immutable leaf components: `StatusBadge`, `Metric`, `Section`. Components contain no rendering logic, no Atlas calls, and no business logic. Views assemble Components; Components never assemble Views.

## PlatformOrchestrationService

`presentation/orchestration/platform.py` selects a collector and delegates to it -- nothing else. It receives all five collectors through **constructor injection**; it never constructs a collector itself (verified by `tests/support/test_platform_bootstrap.py::test_platform_orchestration_service_does_not_construct_collectors_itself`). It contains no business rules, does not render, and owns no persistence or repositories.

## Renderers

`presentation/renderers/base.py` defines three renderers implementing the `Renderer` protocol (`presentation/renderers/registry.py`):

- `JsonRenderer` -- `application/json`, deterministic via `json.dumps(..., sort_keys=True)`.
- `MarkdownRenderer` -- `text/markdown`, one section per view field.
- `CliRenderer(MarkdownRenderer)` -- `text/plain`, strips Markdown headers line-by-line (see "Renderer Defects Fixed" below).

Renderers consume only immutable Views and a `RenderContract` (`presentation/renderers/contract.py`, itself frozen); they never call Atlas or engine code, never compute business meaning, and never mutate their input view. `RendererRegistry` resolves a renderer by name and raises `ValueError` for an unknown name.

## RenderResult

`presentation/renderers/result.py` is a frozen `@dataclass` carrying `content`, `media_type`, `renderer`, and an immutable `metadata` (`MappingProxyType`). It is the sole return type of every renderer.

## Composition Root

Only `atlas/_bootstrap.py` constructs collectors, the renderer registry, and `PlatformOrchestrationService`. No presentation class constructs its own collaborators at runtime, and there is no service locator.

Because `PlatformOrchestrationService`'s collectors each hold a reference back to the live `Atlas` facade (to call its read-model API), presentation wiring cannot be expressed as another field of the `_AtlasServices` dependency-injection dataclass passed to `Atlas.__init__` -- that would require the `Atlas` instance to exist before it exists. `atlas/_bootstrap.py` resolves this in two explicit steps:

1. Construct `Atlas` from `_AtlasServices` (core engine wiring only). At this point `Atlas.get_*_read_model` is already fully functional, since read models only depend on `_AtlasServices` fields.
2. Using that live `atlas` instance, construct the five collectors, then `PlatformOrchestrationService`, then `RendererRegistry`, and attach them with the internal `atlas._bind_presentation(...)` hook -- called exactly once, only from bootstrap.

This is still pure constructor injection at every step; the two-phase shape exists only to break the unavoidable `Atlas -> Orchestration -> Collectors -> Atlas` cycle inherent in the locked design, not to introduce a locator or hidden runtime construction.

### Import Cycle

`atlas/_service.py` imports `presentation.read_models`, `presentation.views`, `presentation.orchestration`, and `presentation.renderers` at module scope (Atlas is the producer/consumer of these types). `presentation/collectors/collectors.py` and `presentation/orchestration/platform.py` therefore cannot import `Atlas` at runtime without creating a circular import. Both modules use `from __future__ import annotations` and import `Atlas` only under `TYPE_CHECKING`, from the **public** `atlas` package (not the private `atlas._service` module) -- satisfying both the no-cycle requirement and the "presentation only imports the public Atlas facade" rule.

## Public API

`Atlas` (`atlas/_service.py`) remains the sole public platform entry point. In addition to its existing command methods, it exposes:

```python
atlas.get_project_dashboard_view(project_id) -> ProjectDashboardView
atlas.get_workflow_status_view(project_id) -> WorkflowStatusView
atlas.get_research_summary_view(project_id) -> ResearchSummaryView
atlas.get_knowledge_summary_view(project_id) -> KnowledgeSummaryView
atlas.get_diagnostics_view(project_id) -> DiagnosticsView
atlas.render(view, renderer: str, contract: RenderContract | None = None) -> RenderResult
```

`render` is a separate operation from view retrieval, as required by the locked design -- callers fetch an immutable view, then independently choose how (or whether) to render it.

## Renderer Defects Fixed During Stabilization

Two defects were found via the golden-output test suite and fixed as in-scope "renderer polish," not architecture changes:

1. **Raw dict repr in Markdown lists.** `MarkdownRenderer` rendered list-of-dict fields (e.g. `sections`, `metrics`) with Python's raw `dict` `repr`, e.g. `- {'title': 'Objective', 'body': 'Ship it'}`. Fixed by a `_format_list_item` helper that renders dict items as `**key**: value` pairs.
2. **`CliRenderer` header corruption.** The original implementation chained `content.replace("# ", "").replace("## ", "\n")`. Because `"## "` contains `"# "` as a substring starting at index 1, the first `.replace("# ", "")` call consumed part of every `"## "` marker before the second call could match it, turning `## Status` into `#Status` instead of a blank line + `Status`. Fixed with a line-by-line `_strip_markdown_headers` helper. Regression-tested in `tests/presentation/test_golden_output.py::test_cli_renderer_does_not_corrupt_h2_markers`.

## Testing

See `tests/architecture/test_presentation_boundaries.py` (dependency boundaries), `tests/presentation/` (components, views, collectors, renderers, golden output), and `tests/support/test_platform_bootstrap.py` + `tests/presentation/test_facade_integration.py` (composition-root wiring and the full Atlas -> Read Model -> Collector -> View -> Renderer -> RenderResult pipeline).

See also [Presentation Flow Diagram](../diagrams/presentation-flow.md) and [Presentation Extension Guide](../guides/presentation-extension-guide.md).
