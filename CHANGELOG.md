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
