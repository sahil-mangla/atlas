# Presentation Layer Extension Guide (Phase 14)

## Purpose
Step-by-step guide for adding a new View kind (a new read-only presentation surface) to the `presentation/` package without violating the locked Phase 14 architecture.

## Responsibilities
- Describe the integration process for a new Read Model, Collector, View, and its wiring through `PlatformOrchestrationService` and the Atlas facade.

## Non-Responsibilities
- Adding a new Renderer format (JSON/Markdown/CLI are the locked set; see "Adding a Renderer" below only if a new output format is genuinely required).
- Any change to engine subsystems -- a new View only ever reads existing Phase 1-13 state.

---

## Adding a New View (e.g. "Evaluation Summary")

### 1. Read Model
Add the new immutable DTO to `presentation/read_models/models.py`:

```python
class EvaluationReadModel(ReadModel):
    project_id: UUID
    exists: bool
    ...
```

Export it from `presentation/read_models/__init__.py`.

### 2. Atlas Read-Model Method
Add `get_evaluation_read_model(self, project_id: UUID) -> EvaluationReadModel` to `Atlas` in `atlas/_service.py`. It must:
- Source data only from an existing Phase 1-13 repository/service already held by `Atlas` (add the repository to `_AtlasServices` as an `Optional[...] = None` field if it isn't already there, mirroring `research_repo`/`planning_repo`/etc., and wire it in `atlas/_bootstrap.py`'s `_AtlasServices(...)` call).
- Return only the immutable DTO -- never the engine domain entity or the repository itself.
- Map any engine exception the same way existing methods do (see `_map_project_exception` / `_map_workflow_exception` for the pattern), or raise a suitable `atlas.exceptions.ApplicationError` subclass directly.

### 3. Component reuse
Prefer the existing `StatusBadge`, `Metric`, `Section` components (`presentation/components/models.py`) before adding a new one. Only add a new Component if none of the three fit, and keep it a frozen leaf with no rendering logic, no Atlas dependency, and no business logic.

### 4. View
Add the frozen View to `presentation/views/models.py`:

```python
class EvaluationSummaryView(View):
    kind: Literal["evaluation_summary"] = "evaluation_summary"
    project_id: UUID
    metrics: tuple[Metric, ...] = ()
```

Add it to the `PresentationView` discriminated union and export it from `presentation/views/__init__.py`.

### 5. Collector
Add a `EvaluationSummaryCollector` to `presentation/collectors/collectors.py`:

```python
class EvaluationSummaryCollector:
    def __init__(self, atlas: Atlas) -> None:
        self.atlas = atlas

    def collect(self, project_id: UUID) -> EvaluationSummaryView:
        model = self.atlas.get_evaluation_read_model(project_id)
        return EvaluationSummaryView(project_id=project_id, ...)
```

It must call only `get_*_read_model` methods on the injected `Atlas` -- never a repository, never another collector, never an engine service.

### 6. PlatformOrchestrationService
Add a new constructor parameter and a `get_evaluation_summary_view` method to `presentation/orchestration/platform.py`. Do **not** construct the collector inside `PlatformOrchestrationService` -- it is received via constructor injection, like every other collector.

### 7. Composition Root
In `atlas/_bootstrap.py`, construct the new collector and pass it into `PlatformOrchestrationService(...)` alongside the existing five, in the presentation-wiring block that runs after `Atlas` is constructed (see "Composition Root" in [Presentation Layer Architecture](../architecture/presentation-layer.md) for why this happens in two phases). Mirror the same addition in `tests/support/test_bootstrap.py::create_test_platform`, which must stay in lockstep with the production bootstrap.

### 8. Atlas Facade Method
Add `get_evaluation_summary_view(self, project_id: UUID) -> EvaluationSummaryView` to `Atlas`, delegating to `self._require_presentation().get_evaluation_summary_view(project_id)`.

### 9. Tests
- **Boundary**: no new test needed -- `tests/architecture/test_presentation_boundaries.py` walks every file under `presentation/` automatically.
- **Component/View**: add immutability tests in `tests/presentation/test_components.py` / `test_views.py` if a new Component was added.
- **Collector**: add a `FakeAtlas.get_evaluation_read_model` method and collector tests in `tests/presentation/test_collectors.py`, following the existing pattern -- the fake must expose *only* the read-model API, proving the collector depends on nothing else.
- **Golden output**: add the new view to the `VIEWS` dict and golden strings in `tests/presentation/test_golden_output.py`.
- **Bootstrap/Facade integration**: extend `tests/support/test_platform_bootstrap.py` and `tests/presentation/test_facade_integration.py` to cover the new collector and view method.

---

## Adding a Renderer

Only add a new renderer if a genuinely new output format is required (e.g. HTML). Do not add one speculatively.

1. Implement a class in `presentation/renderers/base.py` (or a new module under `presentation/renderers/`) satisfying the `Renderer` protocol in `presentation/renderers/registry.py`: a `name: str` attribute and `render(view, contract) -> RenderResult`.
2. It must consume only the immutable view and `RenderContract`, perform formatting only, and never call Atlas or engine code.
3. Register it in the `RendererRegistry(...)` construction inside `atlas/_bootstrap.py` (and `tests/support/test_bootstrap.py`).
4. Add deterministic-output and golden-output tests in `tests/presentation/test_renderers.py` and `test_golden_output.py`.

---

## Common Mistakes to Avoid

- **Importing `atlas._service` instead of `atlas`.** Presentation code must only reference the public `atlas` package (and only under `TYPE_CHECKING`, to avoid the import cycle described in [Presentation Layer Architecture](../architecture/presentation-layer.md)).
- **Constructing a collector inside `PlatformOrchestrationService`.** Collectors are always constructor-injected by the composition root.
- **Calling a repository, engine service, or another collector from inside a collector.** A collector's only collaborator is the injected `Atlas` instance's `get_*_read_model` API.
- **Putting business logic in a renderer.** If a renderer needs to compute something beyond formatting (e.g. "is this healthy"), that computation belongs in the collector, expressed as a field on the View (e.g. `DiagnosticsView.healthy`).
- **Forgetting `tests/support/test_bootstrap.py`.** It mirrors the production `_create_platform()` wiring shape and will not compile if new required `_AtlasServices` fields or presentation wiring are added to one but not the other.
