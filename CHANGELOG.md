# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Phase 17: Release Candidate Stabilization

#### RC-001 -- Workflow Completion Blocker
- Fixed: a project could reach the `iteration` stage and never progress
  further through any public interface. `WorkflowTransitionService.transition_stage`
  sets default active objectives for every stage, including the human-driven
  stages that have no AI `StageExecutor` (`problem_definition`,
  `implementation`, `iteration`, `completion`); those objectives could
  previously only be cleared by `WorkflowProgressService.complete_objective`,
  an engine service that was never exposed through a Command, capability
  method, or CLI command. `workflow transition` therefore permanently failed
  readiness once a project reached one of those stages.
- Added: `CompleteObjectiveCommand` / `Atlas.complete_objective` /
  `atlas workflow complete-objective --project-id <uuid> --objective <o>`,
  delegating to the existing `WorkflowProgressService.complete_objective` (no
  new engine behavior). Also reachable through `Atlas.handle()` for
  non-CLI adapters.
- A project can now reach `idea -> research -> planning -> architecture ->
  review -> iteration -> completion` using only documented public
  interfaces. See `docs/architecture/workflow-stages.md#progressing-through-a-human-driven-stage`.

#### RC-002 -- Knowledge CLI
- Fixed: engineering-knowledge candidates could be extracted and reviewed
  internally (`ReviewKnowledgeCandidateCommand` existed on the `Atlas` facade
  since Phase 13) but had zero CLI exposure -- no parser branch, no
  application dispatch, no renderer -- so a CLI user could never see or act
  on them.
- Added: `atlas knowledge list [--status <s>]`, `atlas knowledge show
  --candidate-id <uuid>`, `atlas knowledge approve --candidate-id <uuid>`,
  `atlas knowledge reject --candidate-id <uuid> --feedback <f>`. Approval
  publishes in the same step (`KnowledgeApprovalService.approve_and_publish`)
  -- there is no separate publish action in the engine, so no `publish`
  sub-command was added.
- Added engine-side plumbing reused by the above (no new business logic):
  `KnowledgeOrchestrationService.list_candidates` /
  `.get_candidate`, thin pass-throughs to the existing
  `KnowledgeRepository.list_candidates` / `.get_candidate`.
- Fixed a latent architecture-boundary leak surfaced while wiring this up:
  `ReviewKnowledgeCandidateCommand` previously took raw
  `engine.domain.knowledge.KnowledgeActor` / `engine.domain.enums.ProposalDecision`
  values, which `clients/` is never allowed to import
  (`tests/test_clients/test_imports.py::test_clients_do_not_import_engine`).
  Added SDK-boundary mirrors (`atlas.types.ProposalDecision`,
  `atlas.types.KnowledgeActorType`, `atlas.commands.KnowledgeActorInput`),
  converted to engine types inside `KnowledgeCapability`.

#### RC-003 -- Presentation CLI
- Fixed: the Phase 14 presentation layer (`Atlas.get_project_dashboard_view`,
  `.get_workflow_status_view`, `.get_research_summary_view`,
  `.get_knowledge_summary_view`, `.get_diagnostics_view`, and generic
  `Atlas.render`) was fully implemented and renderer-agnostic (`cli`,
  `markdown`, `json` via `RendererRegistry`) but had no CLI command group --
  a CLI user could never generate a dashboard or diagnostics report.
- Added: `atlas presentation dashboard|workflow|research|knowledge|diagnostics
  --project-id <uuid> [--format <f>]` (prints to stdout) and `atlas
  presentation export --project-id <uuid> --view <v> --output <path>
  [--format <f>]` (writes to a file). `<f>` defaults to `cli`.
- No new rendering logic: both sub-commands call the existing
  `Atlas.get_*_view` methods and `Atlas.render`; the CLI only routes the
  already-rendered `RenderResult.content` to stdout or a file.
- These are CLI-only command types (`clients/cli/commands.py`), matching the
  existing `VersionCommand`/`HelpCommand` precedent -- Phase 14 views are a
  read-only query API deliberately kept outside the `Atlas._dispatch`
  Command/Result envelope, so `PresentationViewCommand`/
  `PresentationExportCommand` were not added to `atlas.commands`.

#### RC-004 -- Configuration Experience
- Fixed: `.env.example` was stale and incomplete -- it had no AI provider
  section at all (despite `ATLAS_AI_PROTOCOL`/`ATLAS_GEMINI_*`/`ATLAS_AI_*`
  being the variables a first-time user most needs), so first-time setup
  required reading `engine/config.py` to discover them.
- Rewrote `.env.example` with a documented, ready-to-uncomment block for
  every registered AI protocol (`GEMINI`, `ANTHROPIC`, `OPENAI_COMPATIBLE`,
  `OLLAMA`), including OpenAI and LM Studio as named `OPENAI_COMPATIBLE`
  targets (not separate protocols -- there is no distinct engine support for
  them), plus a timeout-tuning note (cloud vs. locally-hosted models).
- Expanded the README's "Configuring an AI Provider" table to match: added
  LM Studio, clarified cloud vs. local, and gave a concrete timeout range
  (`180`-`300`s) for local models instead of just "raised well above the
  default."
- Added regression tests (`tests/test_config.py`) that fail if
  `.env.example` ever again omits a real `Settings` field or a registered
  AI protocol, so this can't silently go stale a second time.

#### RC-005 -- Workflow Documentation Sync
- Fixed: `docs/architecture/engineering-workflow.md`'s "Valid Transitions
  Registry" and ASCII state diagram, and `docs/diagrams/engineering-pipeline.md`'s
  mermaid diagram, were both missing the two "skip an optional manual-detour
  stage" shortcut edges the code has actually supported since the
  Finding-009 stage-resolution fix: `RESEARCH -> PLANNING` and
  `ARCHITECTURE -> REVIEW` (Problem Definition and Implementation have no AI
  `StageExecutor`, so they're optional detours, not mandatory waypoints).
  Both documents now state and draw all nine edges in
  `WorkflowTransitionService.VALID_TRANSITIONS`, not seven.
- Cross-linked `engineering-workflow.md`'s objectives section to
  `workflow-stages.md#progressing-through-a-human-driven-stage` (the
  RC-001 fix), so a reader following the state-machine doc also discovers
  `atlas workflow complete-objective`.
- Added `tests/architecture/test_workflow_docs_sync.py`: a structural guard
  (in the same spirit as the existing
  `tests/architecture/test_platform_boundaries.py`) that fails if the
  pipeline diagram is ever again missing an edge for a transition
  `WorkflowTransitionService.VALID_TRANSITIONS` actually allows, or if
  either workflow doc stops mentioning any `WorkflowStage` member. Verified
  it actually catches the RC-005 bug by re-running it against the pre-fix
  diagram content.

#### RC-006 -- Diagnostics Improvements
- Fixed: `engine/ai/adapters/_http.py::post_json` collapsed every transport
  failure (timeout, rejected API key, DNS failure, 500, ...) into one
  generic `"AI protocol request failed: {error}"` message. A timeout and an
  auth rejection have different fixes (raise `ATLAS_AI_TIMEOUT_SECONDS` vs.
  fix the API key) but produced indistinguishable, unhelpful text.
- `post_json` now recognizes both timeout paths `urlopen` can take (a bare
  `TimeoutError` and one wrapped in a `URLError`) and HTTP 401/403, and
  raises a message that states what happened, why, and the concrete next
  step (raise the timeout to `180`-`300`s; check the `*_API_KEY` value
  against `.env.example`). Other HTTP/transport errors keep a generic but
  still informative message (status code included) -- confirmed a 500
  does *not* get the misleading API-key hint.
- Improved CLI recovery hints (`clients/cli/renderer.py::_RECOVERY_HINTS`)
  for the remaining diagnostics scenarios: `ProjectNotFoundError` now
  mentions the "wrong directory / `ATLAS_WORKSPACE_ROOT`" failure mode
  explicitly (not just "run project list"); `ProjectLifecycleError` now
  states archived projects have no unarchive path and suggests the actual
  next command; `AIProviderError`'s hint now points at reading the
  error text itself first (since it now actually says what to do) instead
  of a generic "this is often transient."
- Added regression tests (`tests/ai/test_http.py`) covering: bare-timeout
  message content, `URLError`-wrapped-timeout message content, 401 and 403
  both get API-key guidance, and a 500 explicitly does *not*.

#### RC-007 -- Minor UX Polish
- Fixed: `CLIRenderer.render_workflow_status` and `.render_commit` called
  `clients.common.formatting.render_list` for objectives/blocking-issues
  without ever overriding its Unicode `'•'` default bullet based on
  `RenderContext.use_unicode` -- a non-Unicode terminal (`_supports_unicode()`
  returning `False`) still saw `•` bullets, only the heading rule and status
  badges actually degraded to ASCII. Added `CLIRenderer._bullet` (mirroring
  the existing `_ellipsis` pattern) and threaded it through all three
  `render_list` call sites.
- Fixed the same gap in `clients/common/formatting.py::render_tree`
  (currently unused by any renderer, but a public shared primitive):
  added a `use_unicode` parameter with an ASCII fallback for its
  box-drawing connectors, matching every other primitive in that module.
- Fixed: `atlas.types.ProposalStatus` (the SDK-boundary mirror of
  `engine.domain.enums.ProposalStatus`, used so `clients/` never has to
  import `engine` directly) was missing two members --
  `PENDING_REVIEW`/`EXPIRED` -- that the engine enum has. Nothing engine-side
  currently assigns either value, so this was latent rather than a live
  crash, but the moment it is wired up, converting the engine status to the
  SDK one would raise `ValueError`. Added the missing members.
- Added `tests/architecture/test_sdk_enum_mirrors.py`: a structural guard
  checking every declared `atlas.types` mirror enum (`ProjectStatus`,
  `WorkflowStage`, `ProposalStatus`, `EvaluationStatus`, `ProposalDecision`,
  `KnowledgeActorType`, `KnowledgeCandidateStatus`) has exactly the same
  members as its `engine.domain.enums` counterpart -- this is what caught
  the `ProposalStatus` drift above, and prevents the next one silently
  recurring for any of the seven mirrors.
- Added `tests/test_clients/common/test_formatting.py` and an ASCII-fallback
  regression test in `tests/test_clients/cli/test_renderer.py` (neither
  `clients/common/formatting.py` nor this specific fallback path had any
  test coverage before this fix).

#### RC-008 -- Post-Release Hardening Audit
A full-repo audit plus a deep-dive on the research/AI-proposal pipeline
found 27 issues ranging from silent data corruption to AI-generated
research proposals that were never actually checked against the real
papers they claimed to cite. Fixed in seven dependency-ordered batches,
each independently tested and committed.

- **Crash-safe persistence**: every `fs_repository.py` (`workflow`,
  `project`, `evaluation`, `architecture`, `planning`, `memory`,
  `knowledge`, `research`, `ai`) wrote JSON/Markdown directly to the live
  file. A crash, kill, or full disk mid-write left a truncated file that
  every later read rejected as corrupt, with no recovery path. Added
  `shared/atomic_write.py::atomic_write_text` (write to a temp file in the
  same directory, fsync, atomic `Path.replace()`) and routed all ten
  direct-write call sites through it. See
  `docs/architecture/persistence.md#4-crash-safe-atomic-writes`.
- **Research grounding actually enforced** (critical): grounding was
  prompt-only -- the LLM was told to reproduce retrieved paper evidence
  verbatim, but nothing checked that it did. A non-compliant or
  hallucinating response was committed as if faithfully grounded. Added
  `external_id` to `ResearchEvidenceDraft`/`Evidence` so retrieved papers
  carry a stable identifier through generation and persistence, and a
  `_check_grounding` hook (run after existing validation in
  `AIEngineeringService.generate()`) that rejects any generated evidence
  entry whose `external_id` doesn't match a retrieved paper, and rejects
  fabricated evidence outright when retrieval found none. See
  `docs/decisions/adr-005-grounded-research-and-repo-native-review.md`.
- **Research retrieval crashes and bias**: `openalex.py` crashed with
  `AttributeError` on a real OpenAlex authorship with `author: null`;
  `arxiv.py` crashed on a malformed `<published>` date, violating the
  `PaperSource` contract that sources never raise. The retrieval
  orchestrator now defends against both by wrapping every `source.search()`
  call and running all three sources concurrently instead of serially.
  Candidates are now round-robin interleaved across sources before
  dedup+cap -- previously, if the first-queried source alone filled the
  candidate budget, every result from the other two sources was silently
  discarded even though they were fully queried. All three sources now
  rate-limit consecutive requests, honoring each provider's policy, and
  report call failures so a total outage can be distinguished (via an
  error log) from a query that genuinely found no papers. arXiv queries
  are now sanitized so ordinary punctuation in a project description can't
  be reinterpreted as arXiv's boolean/field-prefix query syntax.
- **Repository exception handling**: `engine/memory/fs_repository.py`'s
  `save()` didn't wrap `ProjectNotFoundException` like its
  evaluation/architecture/planning siblings, leaking the raw project-layer
  exception. `FilesystemProposalRepository.get_by_id` now wraps
  JSON/field-parsing errors as `InvalidProposalException` instead of
  letting a raw `JSONDecodeError`/`KeyError` escape on a corrupt record.
  `FilesystemConversationRepository.get_by_id` no longer silently
  swallows corruption via a bare `except Exception` -- it now logs the
  specific failure.
- **Planning's missing REVIEW gate**: `PlanningSummaryService
  .freeze_snapshot` had no status guard, unlike evaluation's and
  architecture's equivalents, which both require `REVIEW` status first.
  It could freeze straight from `DRAFT`, or be called repeatedly after
  `APPROVED`. Added the matching guard and updated
  `PlanningProposalTransformer` to call `submit_for_review` before
  freezing, matching the architecture/evaluation transformers' sequence.
- **Orphaned-project rollback**: `ProjectCapability.create_project` left a
  permanently stuck, unusable project behind if workflow initialization
  failed after the project record was already persisted -- every workflow
  operation on it would then fail, and re-creating it under the same name
  hit `ProjectAlreadyExistsError`. Added `ProjectRepository.delete()`
  (minimal scope: removes only the metadata this repository owns, not the
  project directory tree, since a custom `--path` may pre-exist with
  unrelated content) and a rollback path in `create_project`.
- **Knowledge exception leaks**: `KnowledgeCapability.list_candidates`/
  `.show_candidate` called the knowledge repository directly with no
  exception translation, unlike every other capability method. A corrupt
  candidate file raised `KnowledgeException` straight past
  `Atlas.handle()`, which only catches `ApplicationError` -- breaking the
  `ErrorEnvelope` wire contract for any MCP/REST client. Now wrapped and
  translated to `KnowledgeReviewError`, matching the rest of the class.
- **Dead prompt template registered**: `SummaryPromptTemplate` was fully
  implemented but never included in `PromptLoader.load_registry()`.
  Registered against a new minimal `SummaryDraft` model matching its
  existing hardcoded schema, so resolving it no longer hits
  `PromptRegistry`'s `KeyError`.
- **AI adapter schema/response handling**: `gemini.py` (the default
  provider) now flattens Pydantic's `$defs`/`$ref` schema indirection
  before sending it to Gemini -- every non-trivial proposal draft (e.g.
  `ResearchProposalDraft` nesting `ResearchFindingDraft`/
  `ResearchEvidenceDraft`) produces `$defs`/`$ref` via
  `model_json_schema()`, previously forwarded unresolved.  `ollama.py` now
  forwards the actual `response_schema` as Ollama's `format` value instead
  of the generic string `"json"`, so its declared `structured_output=True`
  capability is honest. `anthropic.py` now selects the first content block
  that actually carries a `text` field instead of assuming `content[0]` is
  text -- a leading non-text block previously produced an empty string and
  a misleading downstream parse failure. See
  `docs/architecture/multi-protocol-ai-runtime.md`.
- **CLI export crash and flag parsing**: `presentation export`'s output
  write is now wrapped in try/except, translating `OSError`/
  `UnicodeEncodeError` into a clean `ApplicationError` instead of an
  uncaught traceback. `_parse_flags` now accepts `--flag=value` alongside
  `--flag value`; a flag immediately followed by another flag (value
  omitted) now raises a clear "requires a value" error instead of
  silently consuming the next flag name as the value; a flag specified
  more than once now raises a clear error instead of silently keeping
  only the last value. `RendererRegistry`'s bare `ValueError` is now
  translated to `ApplicationError` at the capability boundary. See
  `docs/usage/cli.md#flag-syntax`.

## [1.0.0] - 2026-07-21

### Phase 16: Production Readiness & Release Engineering

#### Sprint 1 -- Platform Hardening
- Fixed: `KnowledgeCapability.review_knowledge_candidate` no longer surfaces every
  knowledge-review failure as `PlatformErrorCode.UNKNOWN_ERROR`; added
  `KnowledgeReviewError`/`PlatformErrorCode.KNOWLEDGE_REVIEW_ERROR` and per-exception
  mapping matching every other capability.
- Fixed: `WorkflowExecutionCapability.execute_stage` now routes its stage-mismatch
  error through the same engine-exception/mapper pattern as the rest of the codebase
  (no behavior change, consistency only).
- Removed: dead `Settings.debug` / `Settings.log_level` configuration fields --
  declared and documented but never read anywhere in the codebase.
- See `docs/reports/phase-16-sprint-1-platform-hardening.md` for the full report.

#### Sprint 2 -- Codebase Consistency & Engineering Baseline
- Fixed: `ContextPayload.memory_entries` / `knowledge_entry_ids` `default_factory=list`
  vs. `tuple[UUID, ...]` mismatch -- the source of both the 4 pre-existing mypy errors
  and a Pydantic serialization `UserWarning` in the test suite.
- Ruff: resolved all 217 pre-existing violations (dead code, unused imports/variables,
  exception-naming consistency, PEP 695 generic syntax, pathlib usage, line length);
  repository is now Ruff-clean and `ruff format --check`-clean.
- mypy: 0 errors (from 4).
- See `docs/reports/phase-16-sprint-2-code-quality.md` and
  `docs/reports/phase-16-sprint-2-repository-consistency.md`.

#### Sprint 3 -- User Experience
- Fixed: the `"cli"` presentation renderer (`media_type="text/plain"`) no longer
  leaks literal `**bold**` markdown markers into terminal output.
- Added: every `ApplicationError` now renders with a recovery hint at the CLI
  boundary (`clients/cli/renderer.py::_RECOVERY_HINTS`), not just the exception
  name and message.
- Fixed: the CLI now really does detect terminal Unicode support
  (`_supports_unicode()`) instead of hardcoding `use_unicode=True`; truncation
  ellipses now respect it too.
- Removed: dead `RenderContext.use_color` / `.verbose` fields (declared, never
  read anywhere) and the false "ANSI colors" claim in `docs/usage/cli.md`.
- See `docs/reports/phase-16-sprint-3-ux-review.md` for the full report,
  including two documented-but-not-fixed findings (unwired progress reporting;
  diagnostics messages without recovery guidance).

#### Sprint 4 -- Documentation Audit
- Fixed: ADR sequence gap -- renamed `docs/decisions/architecture-baseline-v1.md` to
  `docs/decisions/adr-001-architecture-baseline-v1.md`, completing the ADR sequence
  (Sprint 2 had already determined the missing `adr-001` identifier was intentional,
  a pre-convention document, and deferred the rename to this sprint).
- Fixed: `docs/README.md` (the architecture documentation index) was missing ADR-003,
  ADR-004, the Phase 15 Platform Layer doc, and two Phase 15 diagrams -- added all five
  and updated the header to reflect Phase 13-15.
- Fixed: `docs/architecture/system-overview.md` claimed "11 core subsystems" while
  omitting the Presentation Layer and Platform Layer subsystems entirely (actually 17
  once added); also corrected a false "ANSI terminal strings" output claim.
- Fixed: root `README.md`'s Package Structure section never mentioned `presentation/`.
- Documented, not fixed: no `CONTRIBUTING.md` or `examples/` directory exists (routed
  to Sprint 7, which already owns GitHub templates and example projects); `.env.example`
  remains permission-blocked in this environment (carried forward from Sprint 1).
- See `docs/reports/phase-16-sprint-4-documentation-audit.md` for the full report.

#### Sprint 5 -- End-to-End Validation
- Fixed (critical): `ContextAssemblerService.assemble_context` (`engine/ai/services.py`)
  unconditionally required an approved snapshot for all four subsystems (Research,
  Planning, Architecture, Evaluation) before generating a proposal for *any* stage --
  making it structurally impossible to ever generate the pipeline's first Research
  proposal on a fresh project, in production as well as tests. Now stage-aware: each
  stage only requires the snapshots that must genuinely precede it.
- Fixed: `atlas.results.CommitResult` never surfaced `transition_blocked`/blocking
  issues -- a successful proposal commit whose automatic stage transition was blocked
  by an incomplete readiness review looked identical to a fully-successful one. Added
  `transition_blocked: bool` / `blocking_issues: tuple[str, ...]` (both defaulted,
  additive), wired through `approve_proposal`, and surfaced in `CLIRenderer.render_commit`.
- Fixed: `tests/support/test_bootstrap.py`'s shared test fixture wired
  `commit_service=Mock(spec=ProposalCommitService)` and no `knowledge_orchestration`,
  unlike production's real composition root -- meaning no test had ever exercised a
  real generate -> approve -> commit cycle through the public facade. Now wires the
  same real services as `atlas/_bootstrap.py`.
- Added: `tests/test_atlas/test_end_to_end_validation.py` -- real facade-level
  coverage for a successful stage commit, a reject-then-retry recovery flow, an
  invalid project ID, and an empty project's diagnostics.
- See `docs/reports/phase-16-sprint-5-end-to-end-validation.md` for the full report.

#### Sprint 6 -- Performance Review
- Reviewed (no code changes -- review-only sprint per plan Section 9): startup
  latency, repeated repository loads, duplicated object creation, disk I/O,
  memory growth, long-lived object retention, and algorithmic complexity.
- Documented as Version 2 optimization candidates: `FilesystemProjectRepository
  .get_by_id`'s full-workspace-rescan fallback on a cache miss (O(N) disk reads
  for a not-found lookup); every proposal-commit transformer performing one
  full read-modify-write disk round trip per individual draft item instead of
  one read, N in-memory mutations, and one write; `WorkflowExecutionCapability
  ._pending_proposals`'s unbounded in-process growth for proposals that are
  generated but never reviewed (relevant only once a long-running server
  adapter exists, which is Version 2 scope).
- See `docs/reports/phase-16-sprint-6-performance-review.md` for the full report.

#### Sprint 7 -- Release Engineering
- Fixed (release-blocking): `pyproject.toml`'s `[tool.hatch.build.targets.wheel]`
  package list omitted `presentation/` entirely -- verified by building the wheel
  and inspecting its contents, which confirmed the entire Presentation Layer
  (Phase 14) was missing from every built distribution. A real `pip install` of
  this package (as opposed to running from a source checkout) would have failed
  at import time for any command that renders output. Added `presentation` to
  the package list and re-verified the built wheel now includes it.
- Fixed: `pytest.log`, a stray committed test-run log, was tracked in git despite
  matching no `.gitignore` rule -- untracked it and added `*.log` to `.gitignore`.
- Reviewed: direct dependencies (`google-genai`, `pydantic`, `pydantic-settings`)
  -- the Anthropic/Ollama/OpenAI-compatible AI provider adapters use only the
  standard library's `urllib` (`engine/ai/adapters/_http.py`), so no additional
  vendor SDK dependencies are missing.
- Added: `.github/ISSUE_TEMPLATE/` (bug report, feature request),
  `.github/PULL_REQUEST_TEMPLATE.md`, and `.github/workflows/ci.yml` (pytest,
  mypy, ruff check, ruff format --check on push/PR to `main`) -- none of this
  scaffolding existed before.
- Version: bumped `pyproject.toml` from `0.1.0` to `1.0.0`; consolidated both
  `[Unreleased]` sections (Phase 15 and Phase 16) into this `[1.0.0]` release.
- See `docs/reports/phase-16-sprint-7-release-engineering.md` for the full
  report, including the Release Checklist and the repository-identity decision
  (git remote naming) left for explicit user action rather than performed here.

### Phase 15: Platform Layer

#### Added
- `atlas/capabilities/`: Capability Layer decomposing the `Atlas` facade into five thin delegation classes (`ProjectCapability`, `WorkflowCapability`, `WorkflowExecutionCapability`, `KnowledgeCapability`, `PresentationCapability`), each a pure relocation of pre-existing `Atlas` method logic.
- `atlas/contracts/`: versioned `RequestEnvelope`/`ResponseEnvelope`, the `PlatformErrorCode`/`ErrorEnvelope` error contract with an explicit, completeness-tested mapping from every `ApplicationError` subclass, and `PLATFORM_API_VERSION`/`SCHEMA_VERSION`/`is_compatible()`.
- `atlas/adapters/`: the structural `PlatformAdapter` protocol, `AdapterContext`, `AdapterKind`, and `PlatformCapabilityManifest`.
- `Atlas.handle(RequestEnvelope) -> ResponseEnvelope`: the preferred uniform dispatch entry point for out-of-process/protocol clients (MCP, REST, IDE, AI agents); named `Atlas` methods remain permanently supported for the CLI, tests, and in-process consumers.
- CLI adapter retrofit: `AdapterContext`, `context` property, `negotiate()` -- proves structural `PlatformAdapter` conformance without changing the CLI's dispatch loop.
- New docs: `docs/architecture/platform-layer.md`, `docs/decisions/adr-004-platform-capability-contract-layer.md`, `docs/diagrams/platform-request-dispatch.md`.
- New tests: `tests/contracts/`, `tests/adapters/`, `tests/test_atlas/test_platform_handle.py`, `tests/architecture/test_platform_boundaries.py`.

#### Notes
- Zero changes to `engine/*` or `presentation/*`; zero changes to `Command`/`Result` DTO shapes; zero behavior changes to any existing `Atlas` method.

## [0.1.0] - 2026-07-12

### Added
- Initialized repository structure.
- Defined product identity and tagline.
- Established engineering blueprint file hierarchy.
- Completed the vision document `Blueprint/01-vision.md`.
