# ADR-005: Grounded Research Retrieval, Repo-Native Proposal Review, and Package Distribution

## Status
Partially implemented. Points 1–3 are shipped, one at a time as decided below; point 4 (PyPI distribution) remains proposed and unscheduled.

- **Point 2+3 (Markdown proposals + `atlas-proposals/` in the repo)**: Implemented. See `engine/ai/markdown.py`, `engine/ai/fs_repository.py` (`FilesystemProposalRepository.save`/`archive_approved`/`delete`), and `atlas/capabilities/workflow_execution_capability.py`.
- **Point 1 (grounded research retrieval)**: Implemented. See `engine/research/sources/` (arXiv, Semantic Scholar, OpenAlex clients), `engine/research/retrieval.py` (`ResearchRetrievalService`), and `ResearchAIEngineeringService._augment_context` in `engine/ai/engineering_services.py`. CORE.ac.uk was deferred as decided below.
- **Point 4 (PyPI distribution)**: Not started.

## Context

Four gaps were raised in a working session and confirmed against the current codebase:

1. **Research is not grounded in real sources.** `ResearchCaptureService` (`engine/research/services.py`) already models `ResearchSource` (title + url/reference) and `Evidence` (citation, origin, confidence, tags) — a domain model built for citation-backed research. But nothing populates it that way today. `ResearchPromptTemplate.build()` (`engine/prompt/templates.py:78`) sends project context plus a bare JSON schema to the configured LLM and asks it to invent sources, evidence, findings, and opportunities from its own training knowledge in one shot. There is no retrieval step — no query to arXiv, Semantic Scholar, or any paper index — before generation. The schema for "cite real work first" exists; the pipeline that feeds it does not.

2. **Proposals are stored only as JSON.** `FilesystemProposalRepository.save()` (`engine/ai/fs_repository.py:123`) writes exactly one artifact: `.atlas/proposals/<id>.json`. A `MarkdownRenderer` already exists (`presentation/renderers/base.py`) and is used for CLI display, but nothing persists a rendered Markdown file. A human asked to approve a proposal today has to read raw JSON.

3. **Proposals are invisible in the user's normal workflow.** `.atlas/proposals/` is a dotfolder inside the Atlas-managed workspace. It doesn't surface in a normal file tree, isn't part of a PR diff, and isn't something a user stumbles into. Review currently requires knowing to go looking for it.

4. **Atlas is distributed as a clone, not a package.** The README's Quick Start is `git clone .../atlas.git && cd atlas && pip install .` — there is no PyPI release. This is why "installing" Atlas today means a full second copy of Atlas's own source sitting inside or next to the user's project, rather than an installed CLI leaving behind only its own state.

These four are related but separable: (1) is a retrieval/evidence pipeline change; (2)+(3) are a persistence/placement change to the same proposal artifact; (4) is a packaging/distribution change. None of them require touching the domain model in `engine/domain/research.py` — the schema already supports this.

## Decision

### 1. Grounded research retrieval precedes proposal generation

Insert a retrieval stage into the Research workflow, before `ResearchAIEngineeringService` calls the LLM to synthesize opportunities:

- A new `engine/research/retrieval.py` (name tentative) queries paper sources via their APIs, in this order:
  1. **arXiv** (`export.arxiv.org/api`) — free API, clean Atom/XML, full text extractable from PDF. Best for CS/ML/physics/math.
  2. **Semantic Scholar** (official API) — structured JSON: abstract, citation graph, TLDR summaries, cross-venue coverage. Functionally replaces "Google Scholar" without the scraping problem.
  3. **OpenAlex** — free metadata + open-access full-text link resolution; used to confirm a legally scrapable full text exists before fetching.
  4. **CORE.ac.uk** — open-access aggregator API, fallback when 1–3 don't have a hit.

  **Google Scholar is explicitly excluded as a scrape target** — it has no official API, its ToS prohibits automated access, and it aggressively blocks/CAPTCHAs bots. Any of its value (broad cross-publisher indexing) is already covered by Semantic Scholar's API.
- No scraping of paywalled HTML in any case — a source is only fetched if OpenAlex/the source itself confirms open access.
- For each candidate paper, an LLM extraction pass (reusing the existing `PromptExecutor`) turns raw abstract/full-text into a structured `Evidence` entry: `citation` (formatted reference), `origin` (source name + URL), `summary`, `confidence`.
- These are written through the *existing* `ResearchCaptureService.add_source` / `add_evidence` methods — no new domain types needed.
- Only after evidence is populated does `ResearchPromptTemplate` run its current job: synthesizing findings, constraints, and opportunities *from the collected evidence* — this reframes the existing prompt from "invent evidence" to "reason over evidence," which also lets us tighten the system prompt to require every `Opportunity`/`ResearchFinding` to trace back to `evidence_ids` it already validates today (`ResearchOrganizationService.add_finding` already rejects unknown evidence IDs).

Decided: arXiv, Semantic Scholar, OpenAlex, CORE — no Google Scholar scraping. Non-paper web search (general engineering blogs, docs) is out of scope for this ADR; revisit separately if needed.

### 2 + 3. Proposals render to Markdown and live in the user's repo

- `.atlas/` stays exactly as it is: hidden, engine-owned, regenerable state (proposal JSON, knowledge graph, conversation logs). Nothing about it changes.
- `FilesystemProposalRepository.save()` gains a second write: alongside `.atlas/proposals/<id>.json` (unchanged, remains the machine-readable source of truth used for validation/replay/commit), it renders the same proposal through the existing `MarkdownRenderer` and writes it to a new **repo-visible** directory at the project root: `atlas-proposals/pending/<id>.md`.
- On approval (`ProposalCommitService`), the file moves from `atlas-proposals/pending/` to `atlas-proposals/approved/<id>.md` — a durable, git-diffable, human-readable trail sitting next to the code it describes.
- Naming: `atlas-proposals/`, not `atlas/`, to avoid any collision/confusion with the installed package name once point 4 ships.
- Atlas does not touch the user's `.gitignore`. Both `atlas-proposals/pending/` and `atlas-proposals/approved/` are written as plain files in the repo; whether to commit, gitignore, or PR-review the pending ones is entirely the user's call, made in their own `.gitignore` — not something Atlas decides or scaffolds on their behalf.
- The `.atlas/` JSON remains authoritative for the engine; the Markdown is the human-facing read surface only. If a human edits the Markdown, that edit is *not* fed back automatically — approval/rejection still goes through the existing CLI decision flow. Two-way sync is out of scope here.

Decided: `.atlas/` unchanged and hidden; new `atlas-proposals/{pending,approved}/` visible at repo root, written unconditionally; gitignore/commit choice is left entirely to the user.

### 4. Package distribution instead of source clone

Not scheduled yet — will be picked up as its own phase, sequenced after 1–3. Recorded here for when it is:

- Publish Atlas to PyPI so the documented install path becomes `pipx install <package-name>` (name TBD), not `git clone` + `pip install .`. `git clone` is explicitly ruled out as the v1 install story.
- Standard procedure when we get there: register the package name on PyPI, confirm `pyproject.toml`'s build backend/version metadata (already present), build with `python -m build`, publish via a GitHub Actions release workflow using PyPI's trusted publishing (`pypa/gh-action-pypi-publish`, no stored API tokens) rather than manual `twine upload`.
- Once packaged, a user's project only ever gains `.atlas/` (engine state) and `atlas-proposals/` (from point 2/3) — never a copy of Atlas's own source.

## Consequences

- **Zero domain-model changes.** All four points are additive: a new retrieval module, a second file write, a new repo path, and a release pipeline. `engine/domain/research.py` and the proposal schemas are untouched.
- **Research proposals get slower but become falsifiable.** An extra network round-trip (paper search + fetch) happens before generation; in exchange, opportunities are traceable to real citations instead of LLM recall.
- **Two proposal artifacts to keep in sync.** JSON stays authoritative; Markdown is derived and regenerated on every save, never hand-authored back into JSON. This must be enforced (a regeneration test) so they can't silently diverge.
- **A repo-visible folder becomes part of the user's project.** `atlas/proposals/` will appear in `git status`, PR diffs, and file trees. This is the point of fix #3, but it does mean Atlas is no longer purely additive to a repo's visible surface — worth confirming that's acceptable before shipping.
- **Distribution work is independent of the other three** and can ship on its own timeline without blocking them.

## Open Questions (resolved)

1. ~~Paper source scope for v1~~ — arXiv, Semantic Scholar, OpenAlex, CORE. No Google Scholar scraping.
2. ~~Commit proposals to git?~~ — Atlas writes both folders unconditionally and never edits `.gitignore`; committing vs. ignoring either is entirely the user's choice.
3. Package name and initial distribution channel for point 4 — still open, deferred until that phase starts.
4. ~~Order of implementation~~ — sequenced, one point at a time, not all four together. Next: decide which point ships first.
