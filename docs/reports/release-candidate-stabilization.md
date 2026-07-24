# Phase 17: Release Candidate Stabilization

Status: **all 8 RC items complete.** This report was updated as each RC
item landed rather than written once at the end; see the Release Readiness
Assessment at the bottom for what "complete" does and does not mean.

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

## RC-006 -- Diagnostics Improvements

### Issue

Five error scenarios were named as needing better diagnostics: project not
found, wrong directory, archived project, provider timeout, missing API
key. Auditing `clients/cli/renderer.py::_RECOVERY_HINTS` and the AI
transport layer found: project-not-found, archived-project, and
missing-API-key already had reasonably clear handling (each AI adapter
already raises a specific "X provider requires Y" message before ever
reaching the network); provider-timeout and any HTTP auth rejection did
not -- both collapsed into one indistinguishable generic message.

### Root Cause

`engine/ai/adapters/_http.py::post_json` caught `(HTTPError, URLError,
OSError, json.JSONDecodeError)` as one group and raised
`f"AI protocol request failed: {error}"` for all of them. A `urlopen`
timeout and an HTTP 401 both produced the same-shaped, unhelpful message --
neither told the user what to actually change (`ATLAS_AI_TIMEOUT_SECONDS`
vs. the API key). Separately, `ProjectNotFoundError`'s and
`ProjectLifecycleError`'s CLI recovery hints stated what was true but not
always the most useful next step (e.g. didn't mention the "wrong directory /
`ATLAS_WORKSPACE_ROOT`" cause, or that archived projects have no unarchive
path at all).

### Implementation

- `engine/ai/adapters/_http.py`: split the single `except` clause into one
  for `HTTPError` (checking `error.code` against `{401, 403}` for an
  API-key-specific message, otherwise a generic-but-still-coded message)
  and one for `(URLError, OSError, json.JSONDecodeError)` (checking a new
  `_is_timeout()` helper that recognizes both timeout shapes `urlopen` can
  raise -- a bare `TimeoutError` or one wrapped in `URLError.reason` --
  for a timeout-specific message, otherwise the prior generic message).
  Both new messages name the concrete fix and, for the timeout case, a
  concrete recommended range (`180`-`300`s).
- `clients/cli/renderer.py`: rewrote the `ProjectNotFoundError`,
  `ProjectLifecycleError`, and `AIProviderError` recovery hints to name
  the wrong-directory cause, the no-unarchive-path fact, and to defer to
  the now-actually-useful underlying error text, respectively.

### Audit

- Manually invoked `post_json` with a mocked timeout and a mocked 401 to
  confirm the exact rendered text (see Verification) -- not just that an
  exception type was raised, but that the message a real user would read
  actually explains the fix.
- Confirmed a 500 (or any non-401/403 HTTP error) explicitly does *not* get
  the API-key hint, since that would be actively misleading for e.g. a
  provider outage -- covered by a dedicated test.
- Confirmed missing-API-key was already well handled at the provider-adapter
  layer (e.g. `GeminiAIProvider.generate` raises "Gemini provider requires
  ATLAS_GEMINI_API_KEY and ATLAS_GEMINI_MODEL." before any network call),
  so no change was needed there -- only the network-transport-level 401/403
  case (a key that's present but wrong/expired/revoked) was actually broken.

### Stabilization

- Regression tests added (`tests/ai/test_http.py`): bare-`TimeoutError`
  message content, `URLError`-wrapped-timeout message content, 401 and 403
  both get the API-key hint, and a 500 explicitly does not.

### Affected Files

```
engine/ai/adapters/_http.py
clients/cli/renderer.py
CHANGELOG.md
PROGRESS.md
tests/ai/test_http.py (updated)
```

### Verification

- `pytest`: full suite green, including 5 new/updated `_http.py` tests.
- `mypy .` (strict mode): 0 errors, 268 source files.
- `ruff check .`: all checks passed.
- Manual verification of actual rendered messages:
  - Timeout: `"AI provider request timed out after 60s. If you're using a
    locally-hosted model (Ollama, LM Studio), this is often just slow
    generation on modest hardware, not a real failure -- try raising
    ATLAS_AI_TIMEOUT_SECONDS (e.g. to 180-300) in your .env and retrying."`
  - 401: `"AI provider rejected the request (401 Unauthorized). The
    configured API key is missing, invalid, or lacks access to this model
    -- check the *_API_KEY value in your .env against .env.example, or run
    'atlas presentation diagnostics --project-id <uuid>' to confirm which
    project/stage is affected."`

## RC-007 -- Minor UX Polish

### Issue

Four named sub-items: ASCII fallback for non-Unicode terminals, improve
archived-project messages, improve timeout documentation, improve provider
documentation, stage naming consistency. The latter three were already
substantially covered by RC-004 (provider/timeout docs) and RC-006
(archived-project message) as those RC items were implemented, so RC-007's
audit focused on what was still actually broken: ASCII fallback
completeness and naming/enum consistency across the SDK boundary.

### Root Cause

- **ASCII fallback**: `clients/common/formatting.py::render_list` defaults
  its `bullet` parameter to `'•'` (Unicode) regardless of context -- it has
  no way to know the caller's `RenderContext`. Every other shared rendering
  primitive in that module (`render_heading`, `render_divider`,
  `render_status_badge`, `truncate` via `CLIRenderer._ellipsis`) is
  correctly threaded through `use_unicode`, but `render_list`'s three call
  sites in `CLIRenderer` were not -- an oversight, not a design gap.
  `render_tree` (a public primitive in the same module, currently unused by
  any renderer) had the same gap with no `use_unicode` parameter at all.
- **Stage naming / enum consistency**: `atlas.types` declares seven
  StrEnum mirrors of `engine.domain.enums` types specifically so `clients/`
  code can construct/compare these values without importing `engine`
  directly (the boundary RC-002 fixed a violation of). Nothing checked
  that a mirror and its source stayed in sync member-for-member.
  `atlas.types.ProposalStatus` had drifted -- missing `PENDING_REVIEW` and
  `EXPIRED`, both present on `engine.domain.enums.ProposalStatus`.

### Implementation

- `clients/cli/renderer.py`: added `CLIRenderer._bullet` (mirroring the
  existing `_ellipsis` property) and passed it to all three
  `render_list(...)` call sites (`render_workflow_status` x2,
  `render_commit`).
- `clients/common/formatting.py::render_tree`: added a `use_unicode`
  parameter with ASCII-safe connectors (`` `-- ``/`|-- `/`|   ` instead of
  `└── `/`├── `/`│   `), propagated through its own recursion.
- `atlas/types.py::ProposalStatus`: added the two missing members so it
  exactly mirrors `engine.domain.enums.ProposalStatus` again.

### Audit

- Manually rendered a `WorkflowStatusResult` through `CLIRenderer` with
  `use_unicode=True` and `use_unicode=False` side by side and confirmed
  the ASCII path now has zero non-ASCII bytes anywhere in the output
  (headings, badges, *and* bullets) -- see Verification for the actual
  output.
- Checked every other `atlas.types` mirror enum
  (`ProjectStatus`, `WorkflowStage`, `EvaluationStatus`, `ProposalDecision`,
  `KnowledgeActorType`, `KnowledgeCandidateStatus`) against its engine
  counterpart before writing the fix -- only `ProposalStatus` had actually
  drifted; the RC-001/RC-002 work had kept the others in sync by
  construction.
- Confirmed the two missing `ProposalStatus` members are not currently
  assigned anywhere in engine code (`grep` across `engine/`), so this was
  latent, not a live crash -- but exactly the kind of drift that becomes a
  live `ValueError` the moment engine code starts using them, with no
  warning beforehand without the new guard test.
- Re-audited "stage naming" specifically for the literal `WorkflowStage`
  enum (not just `ProposalStatus`): confirmed `atlas.types.WorkflowStage`
  and `engine.domain.enums.WorkflowStage` already had identical member
  order and values (this is what the new mirror-guard test also checks
  going forward).

### Stabilization

- `tests/architecture/test_sdk_enum_mirrors.py` (new): checks all seven
  declared mirror pairs have identical members; checks the pair-declaration
  table itself isn't referencing a typo'd/renamed name. Confirmed it fails
  against the pre-fix `ProposalStatus` (via `git stash`) and passes
  against the fix.
- `tests/test_clients/common/test_formatting.py` (new): first-ever test
  coverage for `clients/common/formatting.py` -- covers `render_list`'s
  Unicode default and ASCII override, `render_tree`'s Unicode default and
  ASCII fallback (flat and nested), and `truncate`'s Unicode default and
  ASCII override.
- `tests/test_clients/cli/test_renderer.py`: added ASCII-fallback
  regression tests for `render_workflow_status` and `render_commit`,
  asserting `'•'` never appears in `use_unicode=False` output.

### Affected Files

```
clients/cli/renderer.py
clients/common/formatting.py
atlas/types.py
CHANGELOG.md
PROGRESS.md
tests/architecture/test_sdk_enum_mirrors.py (new)
tests/test_clients/common/test_formatting.py (new)
tests/test_clients/common/__init__.py (new)
tests/test_clients/cli/test_renderer.py (updated)
```

### Verification

- `pytest`: full suite green, including all new RC-007 tests.
- `mypy .` (strict mode): 0 errors, 271 source files.
- `ruff check .`: all checks passed.
- Manual side-by-side render of the same `WorkflowStatusResult` in both
  modes:
  ```
  --- Unicode ---            --- ASCII ---
  Workflow Status            Workflow Status
  ═══════════════            ===============
  Readiness: failed  [✗ ...] Readiness: failed  [x ...]
  ── Objectives               -- Objectives
  • Address review feedback  - Address review feedback
  ```

## RC-008 -- Post-Release Hardening Audit

### Issue

Unlike RC-001 through RC-007 (each scoped to one named user-facing gap), RC-008
originated from a full-repo audit run across every subsystem specifically
looking for correctness bugs that would surface under extensive real-world
use rather than a known complaint: silent data corruption, crashes on
realistic-but-untested inputs, and -- most seriously -- an AI-proposal
grounding claim that the code never actually enforced. The audit ran six
parallel subsystem reviews (AI providers, workflow/domain, knowledge/
research, evaluation/architecture/planning/memory repositories,
presentation/CLI, core service/capabilities) followed by two deep-dives on
the research retrieval pipeline and the AI-grounded proposal generation
path, surfacing 27 verified findings.

### Root Cause (by area)

- **Non-atomic writes**: every `fs_repository.py`'s `save()` wrote directly
  to the live file (`path.open("w")` / `write_text()`), with no
  temp-file-then-rename. A crash mid-write left a truncated file; the next
  read raised a domain "invalid/corrupt" exception with no recovery path.
- **Prompt-only grounding**: `ResearchAIEngineeringService._augment_context`
  injected retrieved evidence into the prompt with an instruction to
  reproduce it verbatim, but neither `ResearchProposalValidator` nor
  `PromptExecutor` ever checked the LLM's returned `evidence` array against
  what was actually retrieved -- the instruction was trusted, not verified.
- **Research source contract violations**: `openalex.py` used
  `.get("author", {})`, which only substitutes on a missing key, not an
  explicit `None` -- a real OpenAlex authorship with `author: null` crashed
  with `AttributeError`. `arxiv.py`'s year parser had no exception handling
  around `int(published_el.text[:4])`. Both violate the `PaperSource`
  protocol's explicit "must never raise" contract, and the retrieval
  orchestrator trusted that contract instead of defending against it.
- **Source-order bias in dedup**: `_dedupe` broke out of its loop as soon
  as the candidate cap was reached, so if the first-queried source alone
  filled the cap, candidates from the other two sources were never even
  inspected -- despite both having been fully queried over the network.
- **Divergent repository patterns**: `engine/memory/fs_repository.py`'s
  `save()` was the one sibling (of four near-identical modules) that didn't
  wrap `ProjectNotFoundException`. `PlanningSummaryService.freeze_snapshot`
  was the one sibling (of three) with no `REVIEW`-status guard.
- **Two-step operations with no rollback**: `ProjectCapability
  .create_project` performed project creation and workflow initialization
  as two independent calls with no compensating action if the second
  failed after the first succeeded.
- **Inconsistent exception translation**: every other `KnowledgeCapability`
  method wrapped repository calls and translated `KnowledgeException` to an
  `ApplicationError` subclass; `list_candidates`/`show_candidate` did not.
- **AI adapter correctness**: `gemini.py` forwarded Pydantic's raw
  `$defs`/`$ref` schema output unresolved; `ollama.py` sent the generic
  string `"json"` instead of the actual schema despite declaring
  `structured_output=True`; `anthropic.py` assumed `content[0]` was always
  the text block.
- **CLI edge cases**: the `presentation export` file write had no error
  handling; the flag parser had no `--flag=value` support, silently
  consumed the next flag as a missing value, and silently kept only the
  last value for a repeated flag.

### Implementation

Fixed in seven dependency-ordered batches, each its own commit so
`git bisect` stays tractable:

1. `shared/atomic_write.py::atomic_write_text` (temp file + fsync +
   `Path.replace()`), routed through all ten direct-write call sites.
2. `external_id` added to `ResearchEvidenceDraft`/`Evidence`; a
   `_check_grounding` hook added to `AIEngineeringService.generate()`,
   implemented by `ResearchAIEngineeringService` to reject evidence that
   doesn't match a retrieved paper's `external_id`, and to reject
   fabricated evidence when retrieval found none.
3. Null-safe OpenAlex author parsing; try/except around the arXiv year
   parse; `_search_all_sources` now wraps every source call defensively
   and runs all three concurrently via a thread pool; `_dedupe` now
   interleaves candidates round-robin across sources before capping;
   arXiv queries are sanitized against operator injection; all three
   sources rate-limit consecutive requests and report call failures for
   outage detection.
4. `memory/fs_repository.py.save()` now wraps `ProjectNotFoundException`;
   `FilesystemProposalRepository.get_by_id` wraps parse errors as
   `InvalidProposalException`; `FilesystemConversationRepository.get_by_id`
   logs corruption instead of silently swallowing it; `PlanningSummaryService
   .freeze_snapshot` now requires `REVIEW` status, with
   `PlanningProposalTransformer` updated to call `submit_for_review` first.
5. `ProjectRepository.delete()` added (metadata-only, not the directory
   tree); `create_project` now rolls back on workflow-init failure;
   `KnowledgeCapability.list_candidates`/`.show_candidate` now translate
   `KnowledgeException`; `SummaryPromptTemplate` registered against a new
   `SummaryDraft` model.
6. `gemini.py` flattens `$defs`/`$ref` before sending a schema; `ollama.py`
   forwards the actual schema as `format`; `anthropic.py` selects the
   first content block that actually carries a `text` field.
7. `presentation export`'s write wrapped in try/except; `_parse_flags`
   supports `--flag=value`, rejects a missing value instead of consuming
   the next flag, and rejects a repeated flag instead of silently
   overwriting; `RendererRegistry`'s bare `ValueError` translated to
   `ApplicationError` at the capability boundary.

### Audit

Each batch was verified independently before moving to the next: targeted
new tests were added for the specific defect (e.g. an OpenAlex response
with `author: null`, a proposal draft whose evidence doesn't match
retrieval, a repeated `--name` flag), the affected test suite was run,
then the full suite, `mypy`, and `ruff` were run clean before committing.

### Stabilization

New/extended test coverage per batch: `tests/test_shared_atomic_write.py`
(new); `tests/ai/test_engineering_services.py` (grounding rejection cases);
`tests/research/test_sources.py` and `test_retrieval.py` (null-author,
malformed-date, source-fairness, rate-limit, and outage cases);
`tests/memory/test_repository.py`, `tests/ai/test_repository.py`,
`tests/planning/test_services.py`; `tests/test_atlas/test_project_capability.py`
(new), `tests/test_atlas/test_knowledge_capability.py`,
`tests/ai/test_prompt_management.py`; `tests/ai/test_adapters.py` and
`test_protocol_runtime.py`; `tests/test_clients/cli/test_parser.py` and
`test_presentation_rc003.py`, `tests/presentation/test_facade_integration.py`.

### Affected Files

```
shared/atomic_write.py (new)
engine/{workflow,project,evaluation,architecture,planning,memory,knowledge,research,ai}/fs_repository.py
engine/domain/ai_drafts.py
engine/domain/research.py
engine/ai/engineering_services.py
engine/research/retrieval.py
engine/research/services.py
engine/research/sources/{arxiv,openalex,semantic_scholar,base}.py
engine/planning/services.py
engine/prompt/loader.py
engine/prompt/templates.py
engine/project/repository.py
engine/project/fs_repository.py
engine/ai/adapters/{gemini,ollama,anthropic}.py
atlas/capabilities/{project_capability,knowledge_capability,presentation_capability}.py
clients/cli/application.py
clients/cli/parser.py
CHANGELOG.md
PROGRESS.md
docs/architecture/persistence.md
docs/architecture/multi-protocol-ai-runtime.md
docs/decisions/adr-005-grounded-research-and-repo-native-review.md
docs/usage/cli.md
(plus corresponding test files per batch, listed under Stabilization above)
```

### Verification

- `pytest`: full suite green after every batch and again at the end.
- `mypy` (per `pyproject.toml`): 0 errors across all touched files and a
  full-repo sweep.
- `ruff check .`: all checks passed.
- No existing test was weakened, skipped, or deleted to make any of the
  above pass.

## Release Candidate Stabilization -- Final Summary

### Implementation Summary

All 8 RC items (RC-001 through RC-008) are implemented, each in its own
commit, each preserving backward compatibility, existing architecture, and
engine boundaries per the stated engineering rules. No AI prompts,
research/architecture/planning quality, or engine business logic were
touched at any point beyond what RC-008 itself required to close a
verified correctness gap -- every fix was either (a) wiring an
already-working engine capability through to a public interface that
didn't expose it yet (RC-001, RC-002, RC-003), (b) a documentation/
configuration accuracy fix with a regression test guarding against
recurrence (RC-004, RC-005), (c) an error-message/UX-polish fix with the
same guarantee (RC-006, RC-007), or (d) a correctness/hardening fix found
by systematic audit rather than a reported symptom, each with its own
regression test (RC-008).

### Audit Summary

Every RC item's audit step verified the fix against the actual code (not
assumption) and, wherever practical, confirmed the new regression test
actually fails without the fix (RC-001, RC-002, RC-003 via a real
end-to-end platform; RC-005 and RC-007 via `git stash` + re-run). Two
latent bugs were caught purely by this audit discipline that were not in
the original RC-00X problem statements: the `clients/` -> `engine` import
boundary violation (found while implementing RC-002) and the
`ProposalStatus` SDK-mirror drift (found while implementing RC-007).
RC-008 itself is the largest instance of this pattern -- a
dedicated audit pass (not a user report) that found the research-grounding
enforcement gap, among 26 other issues.

### Test Results

- `pytest`: full suite green as of the RC-008 commits (see each RC section
  above for exact new/updated test files).
- `mypy .` (per `pyproject.toml`): 0 errors, all source files.
- `ruff check .`: all checks passed.
- No existing test was weakened, skipped, or deleted to make any of the
  above pass.

### Remaining Open Issues

- `Settings.environment` (`ATLAS_ENVIRONMENT`) may be dead configuration --
  flagged during RC-004, not fixed there or since, since it touches
  `Settings`'s public shape and needs a deliberate decision, not a
  documentation-scoped fix. See the RC-004 section above.
- `clients/mcp`, `clients/rest`, `clients/ide` were not audited as part of
  Phase 17 -- RC-001 through RC-008 only ever touched the CLI adapter and
  the underlying `Atlas` SDK/engine layers they all share. Commands routed
  through the generic `Atlas.handle()` envelope (everything added in
  RC-001/RC-002) are automatically available to those adapters; the
  CLI-only sentinel commands added in RC-003 (`PresentationViewCommand`/
  `PresentationExportCommand`) are not, by design, since they mirror the
  existing `VersionCommand`/`HelpCommand` CLI-only pattern -- other
  adapters would need their own thin wrapper around the same
  `Atlas.get_*_view`/`Atlas.render` API if they want equivalent
  functionality.
- The Phase 17 problem statement's "Final Deliverable" instructions ask
  this report to include a "Release Readiness Assessment." Per those same
  instructions ("Do not claim the project is release-ready unless every
  release-blocking issue has been verified through tests"): every fix
  described in this report has been verified through tests, run, and
  independently confirmed to fail without the fix where practical. Whether
  ATLAS as a whole is ready for a `v1.0.0` tag is a broader question than
  Phase 17's scope (it also depends on the two open items already tracked
  in `PROGRESS.md`'s Release Checklist -- repository identity/git remote
  naming and the release tag itself, both explicitly left to the user) and
  is not this report's call to make unilaterally.

Do not treat ATLAS as release-ready on the basis of this report alone --
this report documents that RC-001 through RC-008 have each been verified
individually; it is not itself a release sign-off. See `PROGRESS.md` for
current sequencing and the two open release-checklist items left to the
user.
