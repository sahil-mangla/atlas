# Phase 16 -- Sprint 6: Performance Review Report

**Status:** Locked
**Scope:** Repeated repository loads, unnecessary serialization, duplicated object creation, disk I/O, startup latency, algorithmic complexity, memory growth, long-lived object retention.
**Reference:** [docs/plans/phase-16-production-readiness.md](../plans/phase-16-production-readiness.md), Section 9.

This sprint is explicitly **not** an optimization phase (Section 9): its job is to identify and document engineering inefficiencies, not to restructure the architecture around them. Findings below are reviewed and quantified; none are fixed here unless the fix was already a trivial, risk-free byproduct of investigation. All are candidates for a future, evidence-driven optimization pass (Version 2), consistent with the plan's own instruction that "performance improvements should only be implemented when supported by measurable evidence."

---

## 1. Startup Latency -- Reviewed, No Issue Found

- `PromptLoader.load_registry()` constructs five in-memory `PromptTemplate` objects with no I/O and no external calls -- called exactly once, at platform bootstrap (`atlas/_bootstrap.py::_create_platform`), never per-request.
- `FilesystemProjectRepository.__init__` eagerly scans the workspace directory once at construction (`_scan_workspace`), parsing every `project.json` to build an in-memory `UUID -> Path` index. This is a one-time, proportional-to-actual-project-count startup cost, and is the same shape as the persistence architecture's other repositories -- appropriate for a local, filesystem-backed platform with no external database to query.
- Platform composition (`_create_platform`) wires every repository, service, and executor exactly once per process; nothing is reconstructed per request.

## 2. Repeated Repository Loads -- One Real Finding

`FilesystemProjectRepository.get_by_id` falls back to a **full workspace rescan** (`_scan_workspace()`, re-parsing every tracked project's `project.json`) whenever the requested ID isn't already in the in-memory `_project_paths` index -- including for a genuinely nonexistent project ID, which is exactly the common case exercised by every "project not found" error path (confirmed in Sprint 5's `test_invalid_project_id_raises_not_found` and the pre-existing `test_load_nonexistent_project`/`test_get_project_dashboard_view_for_unknown_project_raises`).

This turns every not-found lookup into O(N) disk reads (N = number of projects in the workspace) instead of O(1). At the scale ATLAS is designed for today (a single engineer's local projects, realistically low tens), this is not a measurable problem. It becomes one only if the workspace grows to hold a large number of projects and error paths (or repeated polling) are hit frequently. **Not fixed here** -- no measurable evidence of impact at current scale, and the fallback exists for a legitimate reason (projects added to the workspace externally, outside the running process, must still be discoverable). Flagged as a candidate for a future pass: e.g. a bounded rescan cooldown, or scoping the rescan to check only whether the specific target directory now exists rather than re-parsing the entire workspace.

## 3. Duplicated Object Creation & Disk I/O -- Central Finding

Every proposal-commit transformer (`ResearchProposalTransformer`, `PlanningProposalTransformer`, `ArchitectureProposalTransformer`, `EvaluationProposalTransformer` in `engine/ai/engineering_services.py`) builds its committed snapshot by looping over the AI draft's items and calling one domain-service method per item -- `add_evidence`, `add_finding`, `add_constraint`, `add_assumption`, `add_opportunity` for Research; the equivalent per-item methods for Planning/Architecture/Evaluation. **Each of those per-item service methods independently does a full read-modify-write cycle**: `repository.get_by_project_id()` (full file read + deserialize) -> append one item in memory -> `repository.save()` (full file write, re-serializing the *entire*, ever-growing aggregate).

Concretely, for `ResearchProposalTransformer.transform_and_commit` (`engine/ai/engineering_services.py:214-283`) committing a draft with *E* evidence items, *F* findings, *C* constraints, *A* assumptions, and *O* opportunities, the transformer performs `E + F + C + A + O` separate full read-modify-write round trips against the same growing `research.json` file within a single logical commit -- rather than one read, N in-memory mutations, and one write. Each successive write also re-serializes all previously-added items in the same commit, so the I/O and serialization cost for a single commit grows superlinearly with the draft's total item count, not linearly.

This is real and systemic (the same shape recurs in all four transformers), but:
- It is bounded by realistic AI-proposal sizes -- a single stage's draft realistically contains a handful to a few dozen items, not thousands.
- Fixing it means changing four domain services' per-item method signatures into bulk-accepting equivalents (or adding a "batch" variant), which touches the same services exercised throughout the engine's existing test suite and is exactly the kind of restructuring this sprint's own scope excludes without measured evidence.

**Not fixed here.** Documented as the sprint's central finding and the clearest concrete candidate for a future, measurement-backed optimization pass if proposal sizes in practice grow large enough for the repeated-write cost to become noticeable (e.g. wall-clock timing of `commit_proposal` for a large draft).

## 4. Memory Growth / Long-Lived Object Retention

`WorkflowExecutionCapability._pending_proposals` (`atlas/capabilities/workflow_execution_capability.py`) is an in-process `dict[UUID, tuple[UUID, AIProposal[Any]]]` that caches every proposal returned by `execute_stage`, for the lifetime of the `Atlas` instance. Entries are only removed on a successful `approve_proposal` (line 156: `pop` + `proposal_repo.delete`) -- **a rejected proposal is also removed** (`reject_proposal`, line 197), but a proposal that is generated and then simply never reviewed at all (the client crashes, the user abandons the session, an out-of-process adapter loses the request) stays in this dictionary indefinitely. For a single CLI invocation (the only adapter actually wired to a real `Atlas` instance today -- Section 17's Non-Goals exclude a long-running REST/MCP server for this phase), the process exits after one command, so this is not observable in practice. It becomes a genuine concern only once a long-running server-style adapter (REST/MCP, explicitly Version 2 scope per Section 17) keeps a single `Atlas` instance alive across many requests. Flagged for that future phase rather than fixed now, since bounding this cache today (e.g. a TTL or max-size eviction) would be speculative complexity for a scenario this phase explicitly excludes.

The equivalent `FilesystemProposalRepository` (the persisted counterpart) has no such ambiguity -- it is explicitly keyed by project and cleaned up by the same two call sites, so the finding is scoped to the in-memory cache only.

## 5. Unbounded Aggregate History Growth -- Reviewed, No Action Needed

Research/Planning/Architecture/Evaluation aggregates each retain a `snapshots: list[...]` of every frozen snapshot ever created for a project, never pruned or archived; every read/write of the aggregate deserializes/reserializes the full history. This is bounded in practice: a single project accumulates one snapshot per meaningful stage revision, not per user action -- realistically a handful over a project's lifetime. No action needed at this scale; worth naming so a future change that increases snapshot frequency (e.g. auto-snapshotting on every edit) reconsiders this.

## 6. Algorithmic Complexity Elsewhere -- Reviewed, No Issue Found

- `KnowledgeDeduplicationService.check` (`engine/knowledge/services.py`) does a linear scan over all published and pending knowledge candidates per submission, normalizing title strings on every comparison rather than pre-computing a lookup index. This is the correct approach for near-duplicate title matching (which fundamentally requires a normalized comparison, not just a hash lookup) and is bounded by a single project's knowledge base size -- realistically tens to low hundreds of entries. No measurable concern at this scale.
- `ContextAssemblerService.assemble_context` (fixed for correctness in Sprint 5) fetches all four subsystem aggregates unconditionally regardless of which stage is generating, even when a given subsystem's snapshot isn't required for that stage. This is a deliberate content-enrichment choice (the LLM prompt includes whatever downstream context is already available), not a bug; the extra fetches are four bounded, already-necessary repository calls, not a loop over unbounded data.

## 7. Verification

No source changes were made in this sprint (review-only, per Section 9). Regression suite re-run to confirm the review process introduced no drift:

```
uv run pytest        -> 470 passed
uv run mypy .         -> Success: no issues found in 263 source files
uv run ruff check .   -> All checks passed!
uv run ruff format .  -> 263 files already formatted
```

## 8. Public API / Compatibility Impact

None. No code was changed.

## 9. Sign-off

Sprint 6 is complete per Section 9 of the Phase 16 plan: startup latency, repeated repository loads, duplicated object creation, disk I/O, memory growth, long-lived retention, and algorithmic complexity were each reviewed with concrete evidence from the codebase graph. One systemic inefficiency (Section 3, per-item read-modify-write in proposal commit) and two narrower ones (Sections 2 and 4) were identified and documented as Version 2 candidates rather than fixed, per the sprint's explicit "not an optimization phase" scope and the plan's rule that performance changes require measurable evidence first. **Locked** per Section 3.1 -- reopenable only if a later sprint discovers a release-blocking regression traceable to this sprint's scope.
