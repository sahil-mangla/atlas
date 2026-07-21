# Phase 16 -- Sprint 2: Code Quality Report

**Status:** Locked
**Scope:** Ruff cleanup, mypy cleanup, Pydantic warning, dead code, naming, imports, docstrings.
**Reference:** [docs/plans/phase-16-production-readiness.md](../plans/phase-16-production-readiness.md), Sections 5.2-5.3.

---

## 1. Engineering Baseline (Section 5.3) -- Before / After

| Check | Before Sprint 2 | After Sprint 2 |
|---|---|---|
| `uv run ruff check .` | 217 violations | **0** |
| `uv run ruff format --check .` | 28 files unformatted | **clean (262 files)** |
| `uv run mypy .` | 4 errors | **0** |
| Pydantic serialization `UserWarning` in test suite | 1 (`tests/ai/test_repository.py::test_proposal_repository_survives_recreation`) | **0** |
| `uv run pytest` | passing | **passing** (all tests, no regressions) |

## 2. mypy / Pydantic Warning Fix

**Root cause:** `engine/domain/ai.py`'s `ContextPayload.memory_entries` and
`.knowledge_entry_ids` were typed `tuple[UUID, ...]` but declared with
`default_factory=list` -- a type mismatch mypy caught structurally, and the
*same* mismatch caused a live Pydantic serializer `UserWarning` at runtime whenever
the model was constructed with its defaults.

**Fix:**
- `default_factory=list` -> `default_factory=tuple` in `engine/domain/ai.py`.
- The one production call site that populated these fields with `list`/generator
  output (`engine/ai/services.py::ContextAssemblerService`) updated to construct
  `tuple`s. All test call sites already relied on defaults and needed no changes.

## 3. Ruff: 217 -> 0, by Category

| Rule | Count | Resolution |
|---|---|---|
| E501 (line-too-long) | 140 -> 0 | Mostly resolved by `ruff format .` (a full pass had not been run in a while); the remaining ~50 were long string literals/docstrings the formatter won't rewrap, fixed by hand-wrapping into implicit string concatenation or shortening prose. |
| PLR0913 (too-many-arguments) | 14 -> 0 | All 14 are constructor-injection `__init__`s or domain-record-construction methods with many scalar fields -- the codebase's established, intentional pattern (already precedented at `atlas/capabilities/presentation_capability.py`). Suppressed with `# noqa: PLR0913`, matching that precedent, rather than restructuring signatures (which Section 2's architecture freeze rules out). |
| PLR2004 (magic-value-comparison) | 14 -> 0 | All 14 were `assert len(x) == N`-style test assertions. Added a `tests/**` per-file-ignore in `pyproject.toml` rather than extracting 14 named constants that would only add indirection. |
| F841 (unused-variable) | 10 -> 0 | 8 were test-only "assigned but never asserted on" results, fixed by dropping the assignment (matches an already-bare call two lines away in the same test). 2 were in production code -- see Section 4 below, one of which is a real finding, not just cleanup. |
| PLC0415 (import-outside-top-level) | 10 -> 0 | All 10 were test-only local imports with no functional reason to stay local (no name collisions, no lazy-load need); hoisted to module top-level. |
| UP046 (non-pep695-generic-class) | 7 -> 0 | `class Foo(Generic[T])` -> `class Foo[T]` PEP 695 syntax (project requires Python >=3.13). Verified bounds preserved exactly (e.g. `TypeVar("T", bound=BaseModel)` -> `[T: BaseModel]`) and confirmed with a full mypy + pytest pass, since Pydantic generic-model behavior under PEP 695 syntax was the main risk here. Now-redundant module-level `TypeVar`/`Generic` imports removed. |
| N818 (error-suffix-on-exception-name) | 6 -> 0 | `AIException`, `ArchitectureException`, `EvaluationException`, `KnowledgeException`, `PlanningException`, `ResearchException` all lacked the `# noqa: N818` suppression that the codebase's two other subsystem base exceptions (`ProjectException`, `WorkflowException`) already carry for the exact same reason (deliberate `*Exception`/`*Error` two-tier naming convention). Made consistent. |
| PTH123 / PTH118 (stdlib `open`/`os.path.join`) | 7 -> 0 | Mechanical `pathlib.Path` modernization in test files. |
| ARG002 (unused-method-argument) | 2 -> 0 | One is a test double's interface-conformance parameter (prefixed `_project_id`). The other is a real finding, not just cleanup -- see Section 4. |
| SIM102 / SIM117 (collapsible if / nested with) | 3 -> 0 | Mechanical simplifications, zero behavior change (verified via full test pass). |
| PLR0912 (too-many-branches) | 1 -> 0 | Same domain-record-validation method already carrying `# noqa: PLR0913`; added `PLR0912` to the same suppression rather than restructuring. |
| I001 / RUF100 (import sorting / unused noqa) | auto-fixed | Handled by `ruff check --fix`. |
| B024 (abstract class, no abstract methods) | 1 (newly surfaced) | `AIEngineeringService(ABC)` has no `@abstractmethod` members -- true before this sprint too, but only surfaced once the PEP 695 rewrite changed how ruff parsed the class header. Genuine, pre-existing characteristic: it's marked `ABC` as a "don't instantiate directly" convention, not because anything is actually abstract. Suppressed with `# noqa: B024` and documented in the class docstring rather than restructuring the class hierarchy. |

## 4. Two Findings Surfaced By The Cleanup (Not Just Lint Noise)

These two are genuine, verified logic gaps the lint pass exposed -- reported here
rather than silently "fixed" by guessing at intent, per the same standard applied in
Sprint 1's Platform Hardening Report.

### 4.1 `RequirementCoverageService`-adjacent: unused `p_snap` in `TraceabilityEvaluationService.evaluate_traceability` (`engine/evaluation/services.py`)

The method fetches `r_snap`, `p_snap`, and `a_snap` (research/planning/architecture
snapshots) but only ever uses `r_snap` and `a_snap`. It validates that ADR
`related_planning_tasks` is *non-empty* but never checks -- the way the sibling
driver-to-research-finding check does -- that referenced planning task IDs actually
*exist* in the planning snapshot. `p_snap` was fetched specifically to make that
check possible and never wired in.

**Action taken:** removed the dead fetch (satisfies F841; the fetch had no side
effect and no test depends on it). **Action not taken:** did not add the missing
task-ID-existence validation, since that changes the evaluation engine's actual
findings output -- a behavior change requiring its own test coverage and product
sign-off, out of scope for a lint-driven consistency pass. Flagged here for a
follow-up decision.

### 4.2 `KnowledgeLifecycleService.publish_from_candidate`: unused `publisher` parameter (`engine/knowledge/services.py`)

The method takes `publisher: KnowledgeActor` but never uses it -- `PublishedKnowledge.author`
is populated from `candidate.author` (the original submitter) instead.
`PublishedKnowledge` has no separate field to record who *approved/published* an
entry, so there's currently nowhere for `publisher` to go even if it were used.
Existing test coverage (`tests/knowledge/test_services.py`) can't distinguish the two
sources, because the one test that exercises this passes the same actor as both
`candidate.author` and `publisher`.

**Action taken:** left `author=candidate.author` unchanged and suppressed with
`# noqa: ARG002 -- see Sprint 2 Code Quality Report finding` rather than guessing
whether the fix is "use `publisher` instead" (behavior change) or "drop the unused
parameter" (a Command/API-adjacent signature change) -- either resolution is a
genuine design decision, not a lint fix.

## 5. Dead Code / TODO-FIXME / Naming

- TODO/FIXME markers: 0 repository-wide (confirmed both before and after this sprint).
- No other dead code found beyond what's listed in the F841/ERA sweep above.
- Docstring conventions (Google style, per `pyproject.toml`'s `pydocstyle.convention`)
  were not separately audited beyond what the E501 rewraps touched; a full docstring
  audit is Sprint 4 (Documentation Audit) scope.

## 6. Verification

```
uv run pytest       -> full suite passes, no regressions
uv run mypy .        -> 0 errors
uv run ruff check .  -> 0 violations
uv run ruff format . -> clean
```

## 7. Sign-off

Sprint 2 is complete per Sections 5.2-5.3 of the Phase 16 plan: engineering baseline
is genuinely clean (not just nominally re-run), repository consistency resolved (see
companion Repository Consistency Report), zero regressions. **Locked** per Section
3.1 -- reopenable only if a later sprint discovers a release-blocking regression
traceable to this sprint's scope. Findings 4.1 and 4.2 remain open as documented,
non-blocking follow-ups.
