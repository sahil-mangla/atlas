# Phase 16 -- Sprint 3: UX Review Report

**Status:** Locked
**Scope:** CLI (help, discoverability, progress reporting, diagnostics), Presentation (dashboard, markdown, JSON, CLI rendering), Error Experience.
**Reference:** [docs/plans/phase-16-production-readiness.md](../plans/phase-16-production-readiness.md), Section 6.

---

## 1. Reviewed Surfaces

- **CLI** -- `clients/cli/parser.py`, `clients/cli/renderer.py`, `clients/cli/application.py`, `clients/cli/commands.py`
- **Shared client primitives** -- `clients/common/formatting.py`, `clients/common/progress.py`, `clients/common/rendering.py`
- **Presentation renderers** -- `presentation/renderers/base.py` (`JsonRenderer`, `MarkdownRenderer`, `CliRenderer`), golden-output tests
- **Diagnostics** -- `presentation/collectors/collectors.py`, `DiagnosticsView`/`DiagnosticsReadModel`
- **User-facing docs** -- `docs/usage/cli.md`
- **Error taxonomy** -- all 12 `ApplicationError` subclasses and how they surface at the CLI boundary

## 2. Findings Fixed

| # | Finding | Fix |
|---|---------|-----|
| 1 | The `"cli"` renderer (`CliRenderer`, `media_type="text/plain"`) stripped `#`/`##` markdown headers but never stripped `**bold**` emphasis markers -- a terminal user would see literal asterisks like `- **Project Id**: ...` in output that's supposed to be plain text. This was locked in by an existing golden-output test that asserted the asterisks as correct. | Added `_strip_bold_markers()` (regex-based) to `presentation/renderers/base.py`, applied after header-stripping in `CliRenderer.render()`. Updated the golden string and added `test_cli_renderer_strips_bold_markers` asserting no `**` survives in CLI output. |
| 2 | Every public `ApplicationError` reached the terminal as `{ErrorClassName}: {message}` with zero recovery guidance -- inconsistent with the parser's own `CLIParseError` messages, which already include actionable next steps ("Run 'atlas help' for usage", "Valid: create, load, list, archive."). This directly missed the plan's own Error Experience bar: "what happened, why it happened, possible recovery actions." | Added a `_RECOVERY_HINTS` mapping (one entry per `ApplicationError` subclass) in `clients/cli/renderer.py`, appended to `render_error()`'s output. Added `test_all_application_errors_have_recovery_hints`, mirroring the existing `test_all_application_errors_mapped` completeness-test pattern from Sprint 1's error-code work, so a future `ApplicationError` subclass added without a hint fails the suite instead of silently rendering without one. |
| 3 | `RenderContext.use_color` and `.verbose` were declared, documented ("Whether ANSI color codes are supported" / "Whether verbose/debug output should be included"), and `use_color=True` was explicitly threaded through `CLIApplication.__init__` -- but neither field was ever read by any rendering function. No ANSI color code is emitted anywhere in the codebase. Same dead-configuration pattern as Sprint 1's `Settings.debug`/`log_value` finding. | Removed both fields from `RenderContext`. Confirmed via search that no test constructed `RenderContext` with either field explicitly, so nothing else needed updating. |
| 4 | `docs/usage/cli.md` claimed "The CLI respects the terminal width and capabilities (like Unicode support and ANSI colors)" -- the ANSI-color claim was false (see #3), and `use_unicode` was also never really "respected": `CLIApplication` hardcoded `use_unicode=True` unconditionally, so the fully-built and tested ASCII-fallback path (`use_unicode=False`, exercised by `test_capability_aware_rendering`) never actually triggered for a real user on a non-Unicode terminal. | Added `_supports_unicode()` to `clients/cli/application.py` (mirrors the existing `_terminal_width()` try/except pattern: attempts to encode a sample Unicode glyph with `sys.stdout.encoding`, falls back to `False`), and wired it into the real `RenderContext` construction. Fixed the doc's claim to describe only what's actually true (terminal width + detected Unicode support). |
| 5 | `CLIRenderer` hardcoded the Unicode ellipsis (`…`) in two places (`truncate()` calls, and inline `str(p.id)[:8] + "…"`) with no ASCII fallback, even though `truncate()` already accepted an `ellipsis` override and every other rendering helper in the same class correctly branches on `self._ctx.use_unicode`. Meant a user on a real non-Unicode terminal (now reachable per fix #4) would still see a stray `…` in truncated text. | Added a `CLIRenderer._ellipsis` property returning `…`/`...` based on `self._ctx.use_unicode`, used at all three call sites. |

## 3. Findings Documented, Not Fixed (Genuine Scope Boundary)

| # | Finding | Why not fixed here |
|---|---------|---------------------|
| 6 | `clients/common/progress.py` (`ProgressTracker`, `Spinner`, `render_progress_bar`) is fully built and unit-tested (`test_capability_aware_rendering` exercises `ProgressTracker`/`render_progress_tracker`), but has zero callers anywhere in the actual command-dispatch path. A user running `atlas stage execute` (which triggers a synchronous AI-generation call that can take real wall-clock time) gets no progress feedback at all -- the CLI just blocks silently until the result prints. | Wiring this up requires the AI orchestration layer (`WorkflowOrchestrationService.generate_proposal` -> `AIEngineeringService.generate` -> `PromptExecutor.execute`) to expose incremental progress callbacks, which none of it does today -- `execute_stage` is one blocking call end to end. Building that plumbing is a real architectural change (new callback/observer capability threaded through several layers), which Section 2's architecture freeze rules out for this sprint. Flagged for a deliberate future phase. |
| 7 | `DiagnosticsView.issues` / `DiagnosticsReadModel.issues` carry plain statements ("Workflow not initialized.", "Research not started.") with no recovery action, the same what-without-recovery gap as the `ApplicationError` messages (#2) -- but for read-model diagnostics rather than raised errors. | Fixing this would mean either changing `DiagnosticsReadModel`'s shape (a Phase 14 public read-model contract) or duplicating a hint table across two unrelated code paths for marginal benefit, since diagnostics issues are already fairly self-explanatory ("X not started" -> run the workflow's stage command). Lower priority than #2; left as a candidate for Sprint 4 documentation or a future UX pass rather than a signature change here. |

## 4. Reviewed, No Issue Found

- **CLI discoverability**: `_HELP_TEXT` in `clients/cli/renderer.py` and `docs/usage/cli.md` both enumerate exactly the same command groups/sub-commands that `clients/cli/parser.py::CommandParser` actually supports (`project`, `workflow`, `stage`, `proposal`, `version`, `help`) -- no drift between what's documented and what's implemented.
- **Parse error messages**: every `CLIParseError` raise site already states what's wrong and a concrete next step ("Run 'atlas help' for usage", "Valid stages: ...", "Missing required flags: ..."). No changes needed.
- **JSON output quality**: `JsonRenderer` produces deterministic, sorted-key, indented JSON with a stable `schema_version`/`view_kind` metadata envelope. Golden-output tests already lock this down.
- **Markdown quality**: `MarkdownRenderer`'s heading/section/list structure is consistent and readable; no issues found beyond the CLI-specific bold-marker leak (#1).
- **Dashboard readability**: `presentation/collectors/collectors.py` collectors are small, consistent, and each maps directly to one read model with clear metric/section labels.

## 5. Verification

```
uv run pytest       -> full suite passes, no regressions
uv run mypy .        -> 0 errors
uv run ruff check .  -> 0 violations
uv run ruff format . -> clean
```

## 6. Public API / Compatibility Impact

- **Client-internal only.** `RenderContext`, `CliRenderer`/`CLIRenderer`, and `docs/usage/cli.md` are not part of the versioned `atlas/` platform contract (no `Command`/`Result`/`RequestEnvelope`/`ResponseEnvelope` shape changed). The `CliRenderer` golden-output change is a deliberate, test-documented output-format change of exactly the kind its own module docstring anticipates ("If a renderer's output format changes intentionally, update the golden string in the same commit").
- No `PLATFORM_API_VERSION` bump required.

## 7. Sign-off

Sprint 3 is complete per Section 6 of the Phase 16 plan: CLI, presentation, and error-experience surfaces reviewed; five concrete UX defects fixed with regression coverage; two genuine gaps documented rather than papered over with an out-of-scope architectural change. **Locked** per Section 3.1 -- reopenable only if a later sprint discovers a release-blocking regression traceable to this sprint's scope.
