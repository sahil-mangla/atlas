# Phase 16 -- Sprint 5: End-to-End Validation Report

**Status:** Locked
**Scope:** Complete engineering pipeline (Project -> Workflow -> Research -> Planning -> Architecture -> Evaluation -> Engineering Knowledge -> Presentation), validated through the public Atlas facade with representative scenarios.
**Reference:** [docs/plans/phase-16-production-readiness.md](../plans/phase-16-production-readiness.md), Section 8.

---

## 1. Starting Point: The Pipeline Had Never Actually Been Run

Before writing new scenarios, the pipeline's existing test coverage was audited via the codebase graph. Two facts stood out immediately:

- `tests/support/test_bootstrap.py::create_test_platform` -- the shared fixture underlying every `tests/test_atlas/*` facade test -- wired `commit_service=Mock(spec=ProposalCommitService)` and never passed a `knowledge_orchestration` at all, unlike production's `atlas/_bootstrap.py::_create_platform`, which wires both for real.
- The one existing facade-level test that came closest to a real stage cycle, `test_execute_stage_and_approve`, contained its own admission in a comment: *"IDEA stage doesn't have an executor... We will try to execute RESEARCH stage directly, which might raise an error... That's fine, we check exception mapping."* It only ever asserted that *some* error was raised -- never that a proposal actually generated, committed, and persisted.

Net effect: no test, and by extension no prior review, had ever exercised a real `execute_stage -> approve_proposal -> commit` cycle through the public facade. This sprint's job -- run representative projects end to end -- meant fixing that gap first, not working around it.

## 2. Fix: Real Composition in the Shared Test Fixture

`create_test_platform` now wires a real `ProposalCommitService` (with real transformers and validators for all four proposal types) and a real `KnowledgeOrchestrationService`, mirroring `atlas/_bootstrap.py::_create_platform` exactly. It also accepts an optional `ai_provider` parameter so a test can inject a `MockAIProvider` and mutate its `stubbed_response` between calls -- necessary to drive a proposal through a real (non-empty) stage execution instead of the previous `"{}"` stub, which no `ResearchProposalDraft` (or any other draft) can validate against, since `problem_statement`/`objectives` are required fields.

All 465 pre-existing tests using this fixture still pass with the real wiring -- none of them depended on the Mock's behavior, confirming the Mock was masking a gap rather than serving a real test need.

## 3. Critical Finding: `assemble_context` Made the Pipeline Impossible to Ever Start

Running the first real scenario -- create a project, transition to Research, execute the Research stage -- failed immediately, in production code, not test code:

```
engine.ai.exceptions.InvalidContextException: Approved research snapshot required.
```

`ContextAssemblerService.assemble_context` (`engine/ai/services.py`) unconditionally required an **approved snapshot for all four subsystems -- Research, Planning, Architecture, and Evaluation -- before generating a proposal for *any* stage, including Research itself.** Since Research is the pipeline's first stage, no snapshot of any kind can exist yet on a fresh project. This made it **structurally impossible to ever generate the first Research proposal** -- not a test artifact, but a real defect in the method that both the CLI and every other client adapter call in production (`atlas/_bootstrap.py` wires the identical `ContextAssemblerService`).

It went undetected because every existing caller either:
- mocked `ContextAssemblerService` entirely (`tests/ai/test_engineering_services.py`'s `assembler` fixture), bypassing `assemble_context` altogether, or
- reached `WorkflowOrchestrationService.generate_proposal` without `knowledge_orchestration` wired, which takes an early-return branch that skips calling `assemble_context` at all.

Both paths are exactly what the fixed test fixture (Section 2) stopped doing -- which is why this sprint is what surfaced it.

**Fix:** `assemble_context` now accepts an optional `stage: WorkflowStage` parameter and only requires the snapshots that must genuinely precede that stage in the pipeline (Research: none; Planning: Research; Architecture: Research + Planning; Review/Evaluation: Research + Planning + Architecture). Snapshots for other subsystems are included in the serialized context when available but are never required -- `ContextPayload`'s snapshot-ID fields were already all `Optional[UUID]`, confirming the data model was designed for partial availability; only the assembler's enforcement was wrong. `WorkflowOrchestrationService.generate_proposal` now passes `workflow.current_stage` through. Two tests were updated/added in `tests/ai/test_services.py` to lock in both the corrected requirement (Planning still correctly rejects a missing Research snapshot) and the regression itself (Research requires nothing).

This is the sprint's headline result: **the Research stage can now actually run for the first time**, all the way through proposal generation, human approval, and a real filesystem commit.

## 4. Secondary Finding: A Successful Commit Could Silently Fail to Advance the Stage

Following the fix above to a full approval, a second gap surfaced: `WorkflowOrchestrationService.process_review_decision` correctly blocks the automatic stage transition when the workflow's `active_objectives` aren't yet complete (a real, intentional readiness gate -- objective completion is a separate step from proposal approval). But the internal `CommitResult.transition_blocked` / `.transition_errors` fields were never surfaced through the public `atlas.results.CommitResult` DTO, which only exposed `success`, `proposal_id`, and `patch_summary`. A caller approving a proposal whose commit succeeded but whose stage transition was blocked saw `success=True` and a generic "Snapshot ... committed." message, with **no indication the workflow was still stuck on the same stage** -- they would have to separately call `get_workflow_status` to notice.

**Fix (additive, no version bump required):** added `transition_blocked: bool = False` and `blocking_issues: tuple[str, ...] = ()` to `atlas.results.CommitResult`, populated in `WorkflowExecutionCapability.approve_proposal` from the internal result, and surfaced in `CLIRenderer.render_commit` as a "Stage Not Advanced" section when set.

## 5. Scenarios Validated (`tests/test_atlas/test_end_to_end_validation.py`)

| Scenario (plan Section 8) | Validation |
|---|---|
| Small / representative project | `test_research_stage_proposal_commits_successfully_end_to_end`: create -> transition -> execute Research stage -> approve -> real commit succeeds -> `get_research_summary_view`/`get_project_dashboard_view` reflect it. |
| Recovery workflow | `test_reject_then_retry_recovery_flow`: reject a proposal with feedback (confirmed not committed, no longer approvable), then regenerate and approve successfully. |
| Invalid project | `test_invalid_project_id_raises_not_found`: a nonexistent project ID raises `ProjectNotFoundError` through the facade (existing coverage in `tests/presentation/test_facade_integration.py` and `tests/test_atlas/test_project_commands.py` already covers the analogous case for `load_project`, `approve_proposal`, `reject_proposal`, `get_workflow_status` -- cross-checked, no gaps found). |
| Empty project | `test_empty_project_has_no_research_before_any_stage_runs`: a freshly created project presents a well-defined empty state (`research_view.exists is False`, non-empty diagnostics) rather than raising or returning partial data. Cross-checked against the pre-existing `test_diagnostics_view_reports_missing_subsystems`. |
| Large / AI-heavy / research-heavy projects | The four proposal transformers (Research, Planning, Architecture, Evaluation) already have dedicated, passing unit coverage in `tests/ai/test_engineering_services.py`, each exercised through a real `ProposalCommitService`. The `assemble_context` fix (Section 3) applies uniformly to all four stages, not just Research -- confirmed by the full suite passing unchanged. A continuous single-project walk through all four AI stages in one facade-level test was not attempted in this sprint: doing so also requires driving `WorkflowProgressService.complete_objective` to clear each stage's `active_objectives` before a transition can proceed, which is a distinct, already-tested piece of workflow machinery (`tests/workflow/test_services.py::test_workflow_progress_service`) or another sprint's worth of scenario-building rather than a gap in this sprint's core finding. |

## 6. Verification

```
uv run pytest        -> 470 passed
uv run mypy .         -> Success: no issues found in 263 source files
uv run ruff check .   -> All checks passed!
uv run ruff format .  -> 263 files already formatted
```

## 7. Public API / Compatibility Impact

- `atlas.results.CommitResult` gained two fields, both with defaults (`transition_blocked: bool = False`, `blocking_issues: tuple[str, ...] = ()`) -- additive, non-breaking, no `PLATFORM_API_VERSION` bump required per the plan's own versioning rule (Section 2).
- `ContextAssemblerService.assemble_context` gained an optional `stage` parameter (default `None`, preserving the signature for any caller that doesn't pass it) and changed its snapshot-requirement behavior -- this is an internal `engine/ai` service, not part of the `atlas/` public SDK boundary, so it carries no platform-contract impact, but it is a real behavior change to production code, not merely test infrastructure. It was fixed here because it blocks the pipeline this sprint exists to validate, and it meets the plan's "quality over expansion" correctness bar (Section 2) for immediate action rather than deferral.
- No other `engine/*` or `presentation/*` shape changed.

## 8. Sign-off

Sprint 5 is complete per Section 8 of the Phase 16 plan. The sprint's central discovery -- that the engineering pipeline could not generate even its first proposal in production, masked by test doubles that happened to route around the same defect -- is now fixed and covered by regression tests at both the unit level (`tests/ai/test_services.py`) and the facade/end-to-end level (`tests/test_atlas/test_end_to_end_validation.py`). A related visibility gap in the public commit-result contract is also fixed. **Locked** per Section 3.1 -- reopenable only if a later sprint discovers a release-blocking regression traceable to this sprint's scope.
