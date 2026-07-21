# Phase 16 -- Sprint 7: Release Engineering Report

**Status:** Locked
**Scope:** Package metadata, semantic versioning, release notes, CHANGELOG, dependency review, licensing, repository cleanliness, GitHub templates, example projects, release checklist, repository & release identity.
**Reference:** [docs/plans/phase-16-production-readiness.md](../plans/phase-16-production-readiness.md), Section 10.

---

## 1. Findings Fixed

| # | Finding | Fix |
|---|---------|-----|
| 1 | **Release-blocking.** `pyproject.toml`'s `[tool.hatch.build.targets.wheel]` package list (`["atlas", "engine", "interfaces", "shared", "clients"]`) omitted `presentation/` entirely, despite it being a real, substantial top-level package (Phase 14; 64 graph nodes across 6 subpackages). Verified empirically: building the wheel (`uv build --wheel`) and inspecting its contents confirmed `presentation/` was absent from every built distribution. Any real `pip install` of this package (as opposed to running from a source checkout via `uv run`) would fail at import time the moment any command tried to render output, since `clients/cli/application.py` imports `presentation.orchestration`/`presentation.renderers` directly. | Added `"presentation"` to the packages list. Rebuilt the wheel and re-verified its contents now include `presentation/`. |
| 2 | `pytest.log` (a stray, stale `pytest` run transcript) was tracked in git despite matching no `.gitignore` rule -- a repository-cleanliness defect. | Untracked it (`git rm --cached`) and added `*.log` to `.gitignore`. |
| 3 | Version and CHANGELOG were still at pre-release state: `pyproject.toml` at `0.1.0`, and two separate `[Unreleased]` sections (Phase 15, Phase 16) with no release heading. | Bumped `pyproject.toml` to `1.0.0`. Consolidated both `[Unreleased]` sections into a single `## [1.0.0] - 2026-07-21` release heading (Phase 16 first as the more recent work, Phase 15 preserved below it), matching the existing `[0.1.0]` entry's format. Verified `atlas version` (via `importlib.metadata.version("atlas")`, already dynamic -- no hardcoded string to update) now reports `1.0.0`. |
| 4 | No GitHub issue templates, PR template, or CI workflow existed anywhere in the repository. | Added `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `.github/PULL_REQUEST_TEMPLATE.md`, and `.github/workflows/ci.yml` (runs `ruff check`, `ruff format --check`, `mypy`, and `pytest` via `uv` on push/PR to `main`) -- see Section 4 for why CI wiring is additive scaffolding only, not yet "enforced" in the sense of gating merges. |

## 2. Reviewed, No Issue Found

- **Dependency review.** Direct runtime dependencies are `google-genai`, `pydantic`, `pydantic-settings` -- all declared and used. The other three AI provider adapters (Anthropic, Ollama, OpenAI-compatible; `engine/ai/adapters/`) use only the standard library's `urllib` via a shared `_http.py` helper, so no vendor SDK dependency is missing for them. Dev dependencies (`pytest`, `pytest-cov`, `ruff`, `mypy`, `pre-commit`) are all used by the documented local workflow and CI.
- **Licensing.** `LICENSE` is a standard MIT license, correctly attributed to "ATLAS," already consistent with the package's actual name.
- **Repository branding.** `README.md`, `pyproject.toml` (`name = "atlas"`), and `CHANGELOG.md` all consistently refer to the project as ATLAS; no lingering "STRATA"/"strata" text was found anywhere in documentation (confirmed via `search_code`). No badges exist yet to be inconsistent -- none are added here, since badges (build status, PyPI version) presuppose CI/publishing infrastructure not yet live.
- **Example projects.** None exist. Sprint 4 already routed this decision here: adding examples now, before the repository-identity and CI decisions below are actually acted on, risks writing guidance that has to be rewritten once those land. Recorded as an explicit release-checklist item (Section 5) rather than fixed silently.

## 3. Repository & Release Identity -- Decision Required, Not Executed

`git remote -v` confirms the remote still points to `https://github.com/sahil-mangla/strata.git`, while every in-repository reference (package name, README, docs, CHANGELOG) calls the project ATLAS. Sprint 2's Repository Consistency Report already root-caused this via git history: the project was originally named STRATA and renamed to ATLAS (`394d42b rename project`), but the GitHub remote was never renamed to match.

**This was deliberately left unexecuted in this sprint.** Renaming a GitHub repository (or its remote) is an action against real, shared external state -- unlike every other Sprint 7 change, which was a local file edit. It requires either GitHub-side action (renaming the repository via its settings or the `gh` CLI, which GitHub then auto-redirects the old URL for) or a decision to keep the two names deliberately distinct and document why. Both are legitimate outcomes; only the user can make this call, and doing it unprompted would be exactly the kind of shared-state action this session's operating rules require confirming first. **Recorded as the one open item in the Release Checklist below.**

## 4. CI: Wired, Not Yet Enforced

`.github/workflows/ci.yml` now runs the full verification suite (ruff check, ruff format check, mypy, pytest) on every push and pull request to `main`. This satisfies the plan's request to decide CI's scope for v1.0.0: **CI now exists and runs automatically**, but "enforced" in the sense of a required, merge-blocking status check is a repository *branch protection* setting on GitHub itself -- external configuration this session cannot set (it requires GitHub admin access to the repository settings, not a file in the repo). Documented as a Release Checklist item for the user to enable once the repository is public.

## 5. Release Checklist

| Item | Status |
|---|---|
| Package metadata (`pyproject.toml`) accurate and complete | Done -- `presentation` added to wheel packages; version bumped to `1.0.0` |
| Semantic versioning | Done -- `1.0.0` for the first tagged release, per the plan's own designation of this as "the first tagged release" |
| Release notes / CHANGELOG | Done -- consolidated into `## [1.0.0] - 2026-07-21` |
| Dependency review | Done -- reviewed, no gaps found (Section 2) |
| Licensing | Done -- reviewed, consistent (Section 2) |
| Repository cleanliness | Done -- `pytest.log` untracked, `.gitignore` updated |
| GitHub issue/PR templates | Done -- added |
| CI configuration | Done (runs on push/PR) -- **not yet branch-protection-enforced**; enable required status checks in GitHub repository settings when ready |
| Example projects | **Not done** -- explicitly deferred; add once repository identity (below) is resolved, so examples don't need a second pass for a renamed remote/clone URL |
| **Repository identity (git remote naming)** | **Open -- requires your decision.** Rename the GitHub repository from `strata` to `atlas` (GitHub auto-redirects the old URL), or explicitly keep the name difference and document why. Not performed in this session; see Section 3. |
| Version tag (e.g. `v1.0.0`) | **Not created** -- no git tags exist in this repository yet. Creating and pushing a tag is a shared-state action; left for your explicit instruction rather than performed here. |
| Installation verified | Done -- `uv build --wheel` succeeds, the built wheel now contains every package including `presentation/`, and `uv run atlas version` reports `1.0.0` post-rebuild. |

## 6. Verification

```
uv run pytest        -> 470 passed
uv run mypy .         -> Success: no issues found in 263 source files
uv run ruff check .   -> All checks passed!
uv run ruff format .  -> 263 files already formatted
uv build --wheel      -> succeeds; wheel contents include atlas, engine, interfaces,
                         shared, clients, presentation (verified via zipfile inspection)
uv run atlas version  -> ATLAS  1.0.0
```

## 7. Public API / Compatibility Impact

- No `atlas/` public SDK contract changes.
- `pyproject.toml` version bump and package-list fix are release-packaging changes, not code changes to any Command/Result/Contract shape.
- No `PLATFORM_API_VERSION` bump required.

## 8. Sign-off

Sprint 7 is complete per Section 10 of the Phase 16 plan, with one release-blocking packaging defect found and fixed (Section 1, #1), repository cleanliness restored, GitHub scaffolding added, and the version/CHANGELOG finalized for a `1.0.0` release. Two items remain **explicitly open, by design**, pending your decision: repository identity (rename vs. document) and creating/pushing the `v1.0.0` release tag -- both are actions against shared external state that this session's operating rules require confirming with you first rather than executing unprompted. **Locked** per Section 3.1 for everything else -- reopenable only if a later check discovers a release-blocking regression traceable to this sprint's scope.

With Sprint 7 locked, all seven Phase 16 sprints are complete. Per the plan's Phase Completion criteria (Section "Phase Completion"): all sprints done, all verification gates passing, architecture unchanged, platform stabilized. **ATLAS is ready to be declared Version 1.0.0 Release Candidate**, pending the two open items above.
