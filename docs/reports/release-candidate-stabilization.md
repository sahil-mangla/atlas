# Phase 17: Release Candidate Stabilization

Status: **in progress** -- RC-001 through RC-005 of 7 complete. This report
is updated as each RC item lands rather than written once at the end, so
its "Remaining Issues" section is authoritative for what is still open.

## RC-001 -- Workflow Completion Blocker

### Issue

A project could reach the `iteration` stage of the workflow and never
progress past it through any documented public interface. `atlas workflow
transition` would fail readiness indefinitely, with no way to satisfy it.

### Root Cause

Every workflow transition -- AI-assisted or human-driven -- sets a default
list of active objectives for the newly entered stage
(`DEFAULT_STAGE_OBJECTIVES` in `engine/workflow/services.py`).
`WorkflowReadinessService.evaluate_readiness` fails while any objective
remains active, and `WorkflowCapability.transition_stage` refuses to
transition unless readiness passes.

For AI-assisted stages (`research`, `planning`, `architecture`, `review`),
`WorkflowOrchestrationService.process_review_decision` clears
`active_objectives` the moment the stage's one required proposal is
committed. But `problem_definition`, `implementation`, `iteration`, and
`completion` have no AI `StageExecutor` and therefore no proposal to commit
-- nothing on the AI-assisted path ever runs for them.

The engine already had the correct primitive for this:
`WorkflowProgressService.complete_objective`, which removes one objective
string from `Workflow.active_objectives`. It was simply never wired to
anything reachable from outside `engine/` -- no `Command` in
`atlas/commands.py`, no method on `WorkflowCapability`, no entry in
`Atlas._dispatch`, no CLI sub-command. A human-driven stage was therefore a
guaranteed dead end the moment a project reached one, regardless of how the
project got there.

### Implementation

No new engine behavior was introduced -- `WorkflowProgressService.complete_objective`
already did exactly what was needed. The fix wires the existing service
through every layer of the platform:

- `atlas/commands.py`: `CompleteObjectiveCommand(project_id, objective, actor)`.
- `atlas/capabilities/workflow_capability.py`: `WorkflowCapability.complete_objective`,
  which validates the objective is actually active (raising a typed
  `WorkflowException` rather than silently no-op'ing on a typo), delegates
  to `WorkflowProgressService.complete_objective`, and returns the same
  `WorkflowStatusResult` shape as `transition_stage`/`get_workflow_status`.
- `atlas/_service.py` / `atlas/_bootstrap.py`: named method
  `Atlas.complete_objective`, `_dispatch` table entry (so it is also
  reachable via the generic `Atlas.handle()` envelope used by non-CLI
  adapters), and `WorkflowProgressService` added to the composition root.
- `clients/cli/parser.py`, `clients/cli/application.py`,
  `clients/cli/renderer.py`: `atlas workflow complete-objective
  --project-id <uuid> --objective <o> [--actor <a>]`, plus updated CLI help
  text.

### Audit

- Confirmed via the codebase knowledge graph (`search_graph`/`trace_path`)
  that `WorkflowProgressService.complete_objective` had exactly zero
  incoming call edges from `atlas/` or `clients/` before this change --
  the dead end was structural, not a flaky edge case.
- Confirmed `Atlas.handle()` picks up the new command automatically via the
  existing `_dispatch` dict (no separate wiring needed for REST/MCP/IDE
  adapters that route through the envelope API).
- Confirmed the fix preserves every stated constraint: readiness enforcement
  is unchanged (still fails while objectives remain), human approval is
  unchanged (`transition_stage` still requires `ApprovalStatus.APPROVED`),
  and no state-machine transition (`WorkflowTransitionService.VALID_TRANSITIONS`)
  was touched.

### Stabilization

- Regression tests added:
  - `tests/test_atlas/test_iteration_completion_rc001.py`: full
    `idea -> research -> planning -> architecture -> review -> iteration ->
    completion` run through the public `Atlas` facade only (no direct
    repository access), asserting the workflow was previously stuck at
    `iteration` and now is not; plus a test that completing an unknown
    objective raises rather than silently succeeding.
  - `tests/test_atlas/test_workflow_commands.py`: focused unit tests for
    `complete_objective` clearing objectives and unblocking readiness, and
    rejecting an unknown objective.
  - `tests/test_clients/cli/test_parser.py`: CLI argument parsing for
    `workflow complete-objective`.
  - `tests/test_atlas/test_platform_handle.py`: `Atlas.handle()` parity for
    the new command, and the dispatch-table size assertion updated.
- Existing shared test fixtures (`tests/support/test_bootstrap.py`,
  `tests/test_atlas/test_knowledge_commands.py`) updated for the new
  required `WorkflowProgressService`/`workflow_progress_service`
  constructor arguments.
- Documentation updated: `docs/architecture/workflow-stages.md` (new
  "Progressing through a human-driven stage" section with a worked CLI
  example), `README.md` (Quick Start + CLI Reference table),
  `docs/usage/cli.md`.

### Affected Files

```
atlas/commands.py
atlas/capabilities/workflow_capability.py
atlas/_service.py
atlas/_bootstrap.py
clients/cli/parser.py
clients/cli/application.py
clients/cli/renderer.py
docs/architecture/workflow-stages.md
docs/usage/cli.md
README.md
CHANGELOG.md
PROGRESS.md
tests/support/test_bootstrap.py
tests/test_atlas/test_knowledge_commands.py
tests/test_atlas/test_workflow_commands.py
tests/test_atlas/test_platform_handle.py
tests/test_atlas/test_iteration_completion_rc001.py (new)
tests/test_clients/cli/test_parser.py
```

### Verification

- `pytest`: full suite green (all pre-existing tests plus the new RC-001
  regression tests).
- `mypy .` (strict mode, per `pyproject.toml`): 0 errors, 265 source files.
- `ruff check .`: all checks passed.

## RC-002 -- Knowledge CLI

### Issue

Knowledge extraction and human review both worked internally -- committing
a stage proposal extracts candidates (`KnowledgeOrchestrationService.extract_candidate_from_artifact`),
and `Atlas.review_knowledge_candidate` could approve or reject one -- but
none of it was reachable from the CLI. There was no `atlas knowledge ...`
command group at all.

### Root Cause

`ReviewKnowledgeCandidateCommand` existed on the `Atlas` facade since Phase
13 and was already wired into `Atlas._dispatch`, but `clients/cli/parser.py`
had no `"knowledge"` entry in its group dispatch table, `clients/cli/application.py`
had no matching `isinstance` branch, and `clients/cli/renderer.py` had no
renderer for a knowledge result. Separately, there was no way to list *all*
candidates or fetch one by ID at any layer -- `KnowledgeOrchestrationService`
only exposed `list_pending_candidates`, even though the underlying
`KnowledgeRepository.list_candidates` / `.get_candidate` (used internally by
other services) already supported it.

While wiring the CLI, a second, previously latent issue surfaced:
`ReviewKnowledgeCandidateCommand.actor` and `.decision` were typed as raw
`engine.domain.knowledge.KnowledgeActor` / `engine.domain.enums.ProposalDecision`.
`clients/` code is never allowed to import `engine` directly
(`tests/test_clients/test_imports.py::test_clients_do_not_import_engine`,
part of the layered-architecture rules `atlas/` exists to enforce) -- this
had simply never been exercised because no CLI code had ever needed to
construct a `ReviewKnowledgeCandidateCommand` before.

### Implementation

- `engine/knowledge/orchestration.py`: added `list_candidates` and
  `get_candidate`, thin pass-throughs to the already-existing
  `KnowledgeRepository` methods of the same name (no new engine behavior).
- `atlas/types.py`: added SDK-boundary mirrors `ProposalDecision`,
  `KnowledgeActorType`, `KnowledgeCandidateStatus`.
- `atlas/commands.py`: added `KnowledgeActorInput` (SDK-boundary mirror of
  `KnowledgeActor`), `ListKnowledgeCandidatesCommand`,
  `ShowKnowledgeCandidateCommand`; changed `ReviewKnowledgeCandidateCommand.actor`
  / `.decision` to the new SDK types, closing the boundary leak.
- `atlas/results.py`: added `KnowledgeCandidateResult`, `KnowledgeCandidateListResult`.
- `atlas/capabilities/knowledge_capability.py`: added `list_candidates` /
  `show_candidate`; both new methods and `review_knowledge_candidate` now
  convert SDK types to engine types at the capability boundary (`_to_engine_status`,
  `_to_engine_decision`, `_to_engine_actor`) rather than passing engine
  objects through untouched.
- `atlas/_service.py`: named methods + dispatch entries for both new commands.
- `clients/cli/parser.py`, `clients/cli/application.py`, `clients/cli/renderer.py`:
  `atlas knowledge list [--status <s>]`, `show --candidate-id <uuid>`,
  `approve --candidate-id <uuid> [--feedback <f>]`, `reject --candidate-id
  <uuid> --feedback <f>`, all built from `atlas.commands`/`atlas.types`
  only -- no `engine` import anywhere in `clients/`.
- No separate `publish` sub-command: `KnowledgeApprovalService.approve_and_publish`
  already publishes on approval; adding a distinct publish action would
  have been new engine behavior, which RC-002 explicitly excludes.

### Audit

- Confirmed via `ast`-based scan (the same check
  `test_clients_do_not_import_engine` runs) that no file under `clients/`
  imports from `engine` after this change.
- Confirmed `list_candidates`/`get_candidate` on `KnowledgeOrchestrationService`
  are pure pass-throughs -- no new filtering, validation, or side effects
  beyond what `KnowledgeRepository` already did.
- Confirmed approval and rejection still route through the exact same
  `KnowledgeOrchestrationService.process_candidate_review` /
  `KnowledgeApprovalService` used internally since Phase 13 -- the CLI adds
  a translation layer, not new review logic.

### Stabilization

- Regression tests added:
  - `tests/test_atlas/test_knowledge_cli_rc002.py`: end-to-end via the
    public `Atlas` facade -- commits a research proposal with a real
    finding, confirms a candidate is extracted, then lists, shows, approves
    (confirming it publishes via `get_knowledge_read_model`), and separately
    rejects (confirming it does *not* publish).
  - `tests/test_clients/cli/test_parser.py`: parsing for all four
    `knowledge` sub-commands, including the invalid-status and
    missing-feedback error paths.
  - `tests/test_atlas/test_knowledge_commands.py`: updated for the new
    `KnowledgeActorInput`/SDK-type command shape; assertions now check the
    converted engine-side call arguments.
  - `tests/test_atlas/test_platform_handle.py`: dispatch-table size updated
    (11 -> 13, for the two new commands).

### Affected Files

```
engine/knowledge/orchestration.py
atlas/types.py
atlas/commands.py
atlas/results.py
atlas/capabilities/knowledge_capability.py
atlas/_service.py
clients/cli/parser.py
clients/cli/application.py
clients/cli/renderer.py
docs/usage/cli.md
README.md
CHANGELOG.md
PROGRESS.md
tests/test_atlas/test_knowledge_commands.py (updated)
tests/test_atlas/test_platform_handle.py (updated)
tests/test_atlas/test_knowledge_cli_rc002.py (new)
tests/test_clients/cli/test_parser.py (updated)
```

### Verification

- `pytest`: full suite green.
- `mypy .` (strict mode): 0 errors, 266 source files.
- `ruff check .`: all checks passed.
- Manual CLI smoke test: `atlas knowledge list/show/approve/reject` parse
  correctly and dispatch to the right renderer; `atlas help` documents the
  new group.

## RC-003 -- Presentation CLI

### Issue

The Phase 14 presentation layer -- five typed views
(`get_project_dashboard_view`, `get_workflow_status_view`,
`get_research_summary_view`, `get_knowledge_summary_view`,
`get_diagnostics_view`) plus a generic, renderer-agnostic
`Atlas.render(view, renderer, contract)` backed by `RendererRegistry`
(`cli`, `markdown`, `json` renderers) -- was fully implemented and tested
at the `Atlas` facade level, but had no CLI exposure whatsoever. There was
no `atlas presentation ...` command group.

### Root Cause

Phase 14 deliberately kept views outside the Command/`Atlas._dispatch`
envelope used by mutating operations (see
`docs/architecture/presentation-layer.md`): views are read-only queries
with their own typed API (`Atlas.get_*_view` + `Atlas.render`), not
`Command`/`Result` pairs. `clients/cli/parser.py` and
`clients/cli/application.py` were never updated to call this API -- the
CLI's command groups (`project`, `workflow`, `stage`, `proposal`,
`knowledge`) all map onto `Atlas._dispatch`-registered commands, and
nothing analogous existed for the view API.

### Implementation

- `clients/cli/commands.py`: added `PresentationViewCommand` and
  `PresentationExportCommand`, following the existing
  `VersionCommand`/`HelpCommand` precedent -- CLI-only sentinel types that
  subclass `atlas.commands.Command` but are never added to `atlas.commands`
  or `Atlas._dispatch`, since they wrap a query API, not a mutating one.
- `clients/cli/parser.py`: `atlas presentation
  dashboard|workflow|research|knowledge|diagnostics --project-id <uuid>
  [--format <f>]` and `atlas presentation export --project-id <uuid>
  --view <v> --output <path> [--format <f>]`. `<f>` (`cli`/`markdown`/`json`)
  and `<v>` are validated client-side against the renderers/views the
  production bootstrap actually registers, following the same validation
  pattern already used for `--stage` and `--status`.
- `clients/cli/application.py`: `_get_view(view, project_id)` maps the
  validated view name to the matching `Atlas.get_*_view` call; both new
  dispatch branches then call the *same* `Atlas.render(view, format)` used
  internally, and either write `RenderResult.content` to stdout or to the
  `--output` file. No formatting/rendering logic was added to `clients/` --
  every byte of output comes from the existing `presentation/renderers/`
  implementations.
- `clients/cli/renderer.py`: help text documents the new group and valid
  formats.

### Audit

- Confirmed `clients/cli/application.py` never imports from
  `presentation.*` or `engine.*` -- `_get_view`/the dispatch branches only
  call `Atlas` methods and read `.content` off the returned `RenderResult`,
  so no new type needed importing across the boundary.
- Confirmed the `export` sub-command performs plain file I/O (via
  `pathlib.Path.write_text`) and nothing else -- it is not a new rendering
  path, just an alternate destination for output that already existed.
- Confirmed invalid `--format`/`--view` values are rejected by the parser
  (`CLIParseError`, exit code 2) rather than reaching
  `RendererRegistry.resolve`, which raises a plain `ValueError` that
  `CLIApplication.run` does not catch -- this was verified as a real crash
  risk during implementation and closed by validating client-side before
  any `Atlas` call, matching the existing `--stage`/`--status` pattern.

### Stabilization

- Regression tests added:
  - `tests/test_clients/cli/test_presentation_rc003.py`: end-to-end via a
    real `CLIApplication` + real `Atlas` platform (not mocked) -- creates a
    project, renders all five views in `cli` format, verifies `json` format
    produces parseable JSON with the right `kind`/`project_id`, verifies
    `markdown` format, verifies `export` writes a real file with the
    expected content, and verifies a nonexistent project surfaces
    `ProjectNotFoundError` with exit code 1 rather than crashing.
  - `tests/test_clients/cli/test_parser.py`: parsing for all five views
    (parametrized) plus `export`, including invalid-format and invalid-view
    error paths.

### Affected Files

```
clients/cli/commands.py
clients/cli/parser.py
clients/cli/application.py
clients/cli/renderer.py
docs/usage/cli.md
README.md
CHANGELOG.md
PROGRESS.md
tests/test_clients/cli/test_parser.py (updated)
tests/test_clients/cli/test_presentation_rc003.py (new)
```

### Verification

- `pytest`: full suite green.
- `mypy .` (strict mode): 0 errors, 267 source files.
- `ruff check .`: all checks passed.
- Manual CLI smoke test against a real bootstrapped platform: all five
  views in all three formats, export to a real file, and both error paths
  (`bogus` sub-command, `--format xml`) all produced correct output and
  exit codes.

## RC-004 -- Configuration Experience

### Issue

`.env.example` documented `ATLAS_ENVIRONMENT`, `ATLAS_DEBUG` (a field
removed from `Settings` back in Phase 16 Sprint 1), `ATLAS_WORKSPACE_ROOT`,
and `ATLAS_LOG_LEVEL` -- but had no AI provider section at all, despite
`ATLAS_AI_PROTOCOL` and its per-protocol variables being the block a
first-time user most needs to fill in before `atlas project create` /
`stage execute` will work. It also referenced `ATLAS_DEBUG`, a field that
no longer exists on `Settings`.

### Root Cause

`.env.example` is a static file with nothing enforcing it stays in sync
with `engine/config.py::Settings` or `engine/ai/factory.py::ProtocolFactory`'s
registered protocols. It was written before the AI protocol abstraction
existed and never updated afterward.

### Implementation

- Rewrote `.env.example`: kept the existing `ATLAS_ENVIRONMENT`/
  `ATLAS_LOG_LEVEL`/`ATLAS_WORKSPACE_ROOT` (verified these are real,
  currently-read `Settings` fields -- `ATLAS_DEBUG` was dropped, since that
  field really was removed), and added a fully worked, ready-to-uncomment
  block for each of the four registered AI protocols (`GEMINI`, `ANTHROPIC`,
  `OPENAI_COMPATIBLE`, `OLLAMA`), with OpenAI and LM Studio called out by
  name as `OPENAI_COMPATIBLE` targets (there is no distinct protocol
  adapter for either -- confirmed against `engine/ai/factory.py`'s
  registry). Documented `ATLAS_AI_TIMEOUT_SECONDS` with a concrete
  recommendation (cloud: default is fine; local: `180`-`300`).
- Updated the README's "Configuring an AI Provider" table to match: added
  LM Studio, marked cloud vs. local per protocol, replaced "raised well
  above the default" with the same concrete `180`-`300` range.

### Audit

- Verified every value used in `.env.example`'s per-protocol blocks
  (default endpoints, which fields are required vs. optional, whether an
  API key is needed) directly against each adapter's `generate()`
  validation in `engine/ai/adapters/{gemini,anthropic,ollama,openai_compatible}.py`,
  not from memory or assumption.
- Verified `ATLAS_ENVIRONMENT`/`Environment` is still a real, read
  `Settings` field with test coverage (`tests/test_config.py`) -- kept it
  rather than removing it, since RC-004's scope is documentation accuracy,
  not settings pruning (out of scope; noted below for a future RC/phase:
  `environment` is set but never branched on anywhere outside its own
  declaration, so it may be a dead field, but confirming that and deciding
  what to do about it is a separate, deliberate decision, not a documentation
  fix).

### Stabilization

- Regression tests added (`tests/test_config.py`):
  - `test_env_example_documents_every_settings_field`: fails if any real
    `Settings` field's `ATLAS_*` env var is missing from `.env.example`.
  - `test_env_example_documents_every_registered_ai_protocol` +
    `test_known_ai_protocols_are_exhaustive`: fails if a registered AI
    protocol name is missing from `.env.example`, or if the protocol list
    the test guards against drifts from what `ProtocolFactory` actually
    constructs.

### Affected Files

```
.env.example
README.md
CHANGELOG.md
PROGRESS.md
tests/test_config.py (updated)
```

### Verification

- `pytest`: full suite green (including the two new drift-guard tests).
- `mypy .` (strict mode): 0 errors, 267 source files.
- `ruff check .`: all checks passed.

### Note for a future RC

`Settings.environment` (`ATLAS_ENVIRONMENT`) is read and tested but not
branched on by any production code path outside `engine/config.py` itself
-- it may be genuinely dead, matching the `debug`/`log_level` cleanup
Phase 16 Sprint 1 already did once. Confirming and removing it (if
warranted) belongs to a future stabilization pass, not RC-004, since it
touches `Settings`'s public shape and has test-file callers.

## RC-005 -- Workflow Documentation Sync

### Issue

Two living documents that claim to describe the workflow state machine
were stale against the actual code: `docs/architecture/engineering-workflow.md`
(prose transition list + ASCII diagram) and
`docs/diagrams/engineering-pipeline.md` (mermaid diagram).

### Root Cause

`WorkflowTransitionService.VALID_TRANSITIONS` (`engine/workflow/services.py`)
allows two "skip an optional manual-detour stage" shortcut edges --
`RESEARCH -> PLANNING` and `ARCHITECTURE -> REVIEW` -- because
`PROBLEM_DEFINITION` and `IMPLEMENTATION` have no AI `StageExecutor` and are
therefore optional detours, not mandatory waypoints (this is an intentional,
already-comment-documented design decision in the code itself, not new).
Neither doc was updated when that design decision was made: both showed
only seven of the nine actual edges, undercounting the legal paths through
the workflow.

### Implementation

- `docs/architecture/engineering-workflow.md`: added the two missing edges
  to the "Valid Transitions Registry" prose list (with the same
  "optional detour, not mandatory waypoint" rationale already in the code
  comment), and a note above the ASCII diagram pointing at the mermaid
  diagram for the version that actually draws all nine edges. Also added a
  cross-link from the objectives section to
  `workflow-stages.md#progressing-through-a-human-driven-stage` (the RC-001
  fix) so a reader following the state-machine doc discovers `atlas
  workflow complete-objective` rather than hitting the same dead end
  RC-001 fixed.
- `docs/diagrams/engineering-pipeline.md`: added the two missing mermaid
  edges (`Research --> Planning`, `Architecture --> Review`, both labeled
  "Skip ..."), plus a note stating the diagram now matches
  `VALID_TRANSITIONS` exactly.

### Audit

- Audited every other doc under `docs/` that mentions workflow stages
  (`docs/glossary.md`, `docs/README.md`, `docs/architecture/system-overview.md`,
  `docs/architecture/extension-guide.md`, `docs/architecture/architecture-principles.md`,
  `docs/architecture/workflow-stages.md`, `docs/usage/cli.md`, `README.md`)
  for the same class of drift -- none of the others enumerate the full
  transition graph, so none had this bug. `docs/plans/*.md` were
  deliberately left untouched: they are historical records of what was
  planned at the time (like commit messages), not living documentation.
- Confirmed, by temporarily reverting the two doc fixes and re-running the
  new test, that the added regression test actually fails against the
  pre-fix content (not a vacuous assertion) -- see Stabilization below.

### Stabilization

- Added `tests/architecture/test_workflow_docs_sync.py`, alongside the
  existing structural guards in that directory
  (`test_platform_boundaries.py`, `test_presentation_boundaries.py`):
  - `test_pipeline_diagram_has_an_edge_for_every_valid_transition`: for
    every `(source, target)` pair in
    `WorkflowTransitionService.VALID_TRANSITIONS`, asserts a matching
    mermaid edge exists in the diagram file.
  - `test_engineering_workflow_doc_lists_every_stage` /
    `test_workflow_stages_doc_lists_every_stage`: asserts every
    `WorkflowStage` member is mentioned in the corresponding doc.

### Affected Files

```
docs/architecture/engineering-workflow.md
docs/diagrams/engineering-pipeline.md
CHANGELOG.md
PROGRESS.md
tests/architecture/test_workflow_docs_sync.py (new)
```

### Verification

- `pytest`: full suite green, including the new doc-sync guard.
- `mypy .` (strict mode): 0 errors, 268 source files.
- `ruff check .`: all checks passed.
- Confirmed the new test fails against the pre-fix diagram/doc content
  (via a temporary `git stash` of just those two files) and passes against
  the fix.

## Remaining Issues

RC-006 through RC-007 are not yet started:

- RC-006 -- Diagnostics Improvements
- RC-007 -- Minor UX Polish

Do not treat ATLAS as release-ready on the basis of this report alone --
only RC-001 through RC-005 have been verified. See `PROGRESS.md` for
current sequencing.
