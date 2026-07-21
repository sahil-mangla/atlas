# Phase 16 — Sprint 1: Platform Hardening Report

**Status:** Locked
**Scope:** `atlas/` public SDK -- commands, results, contracts, exceptions, types, capabilities, bootstrap; `engine/config.py`; `clients/cli/application.py` bootstrap/error boundary.
**Reference:** [docs/plans/phase-16-production-readiness.md](../plans/phase-16-production-readiness.md), Section 4.

---

## 1. Reviewed Surfaces

- **Atlas SDK** -- `atlas/__init__.py`, `atlas/_service.py`, `atlas/_bootstrap.py`
- **Commands** -- `atlas/commands.py`
- **Results** -- `atlas/results.py`
- **Contracts** -- `atlas/contracts/envelope.py`, `atlas/contracts/errors.py`, `atlas/contracts/version.py`
- **Capabilities** -- all five (`atlas/capabilities/*.py`)
- **Adapters** -- `atlas/adapters/protocol.py`
- **Configuration** -- `engine/config.py` (`Settings`), `engine/ai/config.py` (`ProviderConfig`)
- **Versioning** -- `PLATFORM_API_VERSION`, `SCHEMA_VERSION`, `is_compatible()`
- **Logging** -- reviewed for presence/consistency, not implementation depth (see Finding 4)
- **Error handling** -- every capability's internal exception-to-`ApplicationError` mapping, `to_error_envelope`, CLI boundary handling in `clients/cli/application.py`
- **Bootstrap** -- `_create_platform()` wiring order and the CLI's fallback error path in `main()`

## 2. Findings

### Fixed

| # | Finding | Severity | Fix |
|---|---------|----------|-----|
| 1 | `KnowledgeCapability.review_knowledge_candidate` caught `(WorkflowException, KnowledgeException)` and re-raised the bare `ApplicationError` base class. `_ERROR_CODE_MAP` has no entry for the base class, so every knowledge-review failure surfaced through `Atlas.handle()` as `PlatformErrorCode.UNKNOWN_ERROR` -- the code the platform's own contract docstring reserves exclusively for "a programming defect... never routine application behavior." A rejected or invalid knowledge-candidate review is routine application behavior, not a defect. Every other capability (`Project`, `Workflow`, `WorkflowExecution`) maps each engine exception to a specific `ApplicationError` subclass; `Knowledge` was the one exception. | Correctness / contract-stability | Added `KnowledgeReviewError` (`atlas/exceptions.py`) and `PlatformErrorCode.KNOWLEDGE_REVIEW_ERROR` (`atlas/contracts/errors.py`, additive -- 11 → 12 entries in `_ERROR_CODE_MAP`). Gave `KnowledgeCapability` its own `_map_workflow_exception`/`_map_knowledge_exception` methods mirroring the pattern already used by every other capability. Added `tests/test_atlas/test_knowledge_capability.py` (6 tests) asserting the mapping and that the wire-level code is no longer `UNKNOWN_ERROR`. |
| 2 | `WorkflowExecutionCapability.execute_stage` raised `InvalidTransitionError` (the `ApplicationError` subclass) directly on a stage mismatch, instead of raising the engine-level `InvalidTransitionException` and letting the existing `_map_workflow_exception` translate it -- the pattern every other error path in the same method, and `WorkflowCapability.transition_stage`, already follows. No externally observable behavior changed (the same `ApplicationError` subclass is still raised), but the internal pattern was inconsistent. | Consistency | Changed the raise to `InvalidTransitionException`, routed through the existing `except WorkflowException` / `_map_workflow_exception` path. |

### Fixed (follow-up)

| # | Finding | Severity | Fix |
|---|---------|----------|-----|
| 4 | `Settings.log_level` and `Settings.debug` (`engine/config.py`) were declared, documented ("Enable debug logging and verbose error outputs" / "Logging level...") and exposed via `ATLAS_LOG_LEVEL`/`ATLAS_DEBUG` env vars, but nothing in the codebase read either field -- no `import logging` existed anywhere outside this one declaration. The configuration promised behavior that did not exist. | Consistency / dead configuration | Confirmed zero references anywhere (`.py`, `.md`) beyond the field declarations and their own tests, then deleted both fields from `Settings` and updated `tests/test_config.py` accordingly (default-value and override assertions removed). `Settings` is internal to the composition root (`engine/config.py`, not part of the `atlas/` public SDK), so this is not a public API change. **Note:** `.env.example` could not be checked or edited in this session -- it sits behind a permission rule that blocks Read/Bash access to it. If it references `ATLAS_DEBUG`/`ATLAS_LOG_LEVEL`, those lines should be removed manually. |

### Deferred (documented, not fixed -- would require a contract or scope change out of Sprint 1's bounds)

| # | Finding | Why deferred |
|---|---------|--------------|
| 3 | `ReviewKnowledgeCandidateCommand` (in the public `atlas/commands.py`) takes `decision: ProposalDecision` and `actor: KnowledgeActor`, imported directly from `engine.domain.enums` / `engine.domain.knowledge`. Every other public Command/Result field draws exclusively from `atlas/types.py`'s hand-mirrored "stable scalar types" (e.g. `WorkflowStage` is a distinct enum from `engine.domain.enums.WorkflowStage`, deliberately re-declared to decouple the public wire contract from engine internals). This one Command breaks that boundary -- a caller must import two engine-internal types to construct it, and `KnowledgeActor` is a structured engine domain model, not a scalar. Confirmed via `tests/test_atlas/test_knowledge_commands.py`: the only code in the repo that constructs this command imports straight from `engine.domain.*`; it is not wired into the CLI or any other adapter today. | Changing the field types to public mirrors would be a breaking Command shape change under `PLATFORM_API_VERSION`'s own rule ("changing a field's type... requires a PLATFORM_API_VERSION major bump"). Section 13's "Public APIs are frozen" and Section 2's "Preserve Compatibility" rule out a v1.0.0 fix. Recommend addressing as an additive v2 change: introduce public mirrors in `atlas/types.py`/`atlas/commands.py`, deprecate the engine-typed fields, without removing them until a major bump. |

### Reviewed, no issue found

- **Error-code completeness**: `_ERROR_CODE_MAP` now covers all 12 concrete `ApplicationError` subclasses (enforced by `tests/contracts/test_errors.py::test_all_application_errors_mapped`, count assertion updated 11 → 12).
- **Project/Workflow exception mapping**: `ProjectException` (4 subclasses) and `WorkflowException` (2 subclasses) are fully and correctly mapped in every capability that catches them.
- **AI exception mapping**: `AIException`'s 5 subclasses are not all individually named in `_map_ai_exception`, but the unnamed two (`ConversationNotFoundException`, `InvalidConversationException`) correctly fall through to the generic `AIException -> StageExecutionError` branch -- a real, mapped `PlatformErrorCode`, not `UNKNOWN_ERROR`. This is a deliberate, working fallback, unlike Finding 1.
- **Envelope/version contracts**: `RequestEnvelope`/`ResponseEnvelope`/`PLATFORM_API_VERSION`/`is_compatible()` are internally consistent and well-documented; no changes needed.
- **Configuration defaults**: `Settings` defaults (`workspace_root=./workspace`, `environment=development`, `ai_protocol=GEMINI`) are sensible for local-first usage; no changes needed.
- **Bootstrap wiring order** (`_create_platform()`): dependency order (repositories → project services → AI components → subsystem services → AI engineering services → stage executors → workflow orchestration → facade assembly → presentation binding) is correct and matches the documented two-phase composition-root contract; no changes needed.

## 3. Verification

```
uv run pytest       -> full suite passes (all tests green, no failures)
uv run mypy .        -> 4 pre-existing errors, unchanged from Sprint 1 entry baseline (Section 5.3 of the plan);
                        all newly touched files (including new test file) are mypy-clean
uv run ruff check .  -> 217 pre-existing violations, unchanged from Sprint 1 entry baseline;
                        all newly touched files are ruff-clean
```

No new mypy or ruff violations were introduced. The pre-existing 217/4 counts are explicitly Sprint 2's baseline to resolve, per Section 5.3 of the Phase 16 plan, and were left untouched here to keep this sprint's diff scoped to platform-hardening changes only.

## 4. Public API / Compatibility Impact

- **Additive only.** One new `ApplicationError` subclass (`KnowledgeReviewError`) and one new `PlatformErrorCode` member (`KNOWLEDGE_REVIEW_ERROR`) were added. No existing Command, Result, error code, or exception type was removed, renamed, or changed shape.
- No `PLATFORM_API_VERSION` bump required (additive error taxonomy growth is within the existing "gain new... within a major version" policy for the contract layer).

## 5. Sign-off

Sprint 1 is complete per Section 4 of the Phase 16 plan: public API unchanged (net-additive only), regression suite passes, no behavioral regressions. **Locked** per Section 3.1 -- reopenable only if a later sprint discovers a release-blocking regression traceable to this sprint's scope.
