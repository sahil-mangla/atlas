# ATLAS

**Where Ideas Become Engineering.**

[![PyPI](https://img.shields.io/pypi/v/atlas-eng)](https://pypi.org/project/atlas-eng/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![CI](https://github.com/sahil-mangla/atlas/actions/workflows/ci.yml/badge.svg)](https://github.com/sahil-mangla/atlas/actions/workflows/ci.yml)

ATLAS is an AI-native engineering operating system that transforms ideas into
production-ready software through structured research, architecture, planning,
implementation, verification, and persistent project intelligence.

Rather than a chat window bolted onto a code editor, ATLAS models software
engineering as a disciplined, auditable pipeline: every AI-generated proposal
is reviewed and explicitly approved by a human before it becomes part of the
project's permanent record. Nothing an AI drafts is ever silently committed.

---

## Table of Contents

- [What ATLAS Does](#what-atlas-does)
- [Quick Start](#quick-start)
- [Configuring an AI Provider](#configuring-an-ai-provider)
- [Optional Features](#optional-features)
- [CLI Reference](#cli-reference)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)
- [Project Status](#project-status)

---

## What ATLAS Does

Every project moves through the same four-stage engineering pipeline:

```
  Research  ─────▶  Planning  ─────▶  Architecture  ─────▶  Evaluation
  (problem,          (scope,           (components,          (readiness
   evidence,          milestones,       decisions,            review,
   findings)          tasks)           interfaces)           knowledge)
```

For each stage, ATLAS:

1. **Generates a draft proposal** using your configured AI provider, grounded
   in the project's accumulated context (prior approved research, plans, and
   architecture decisions). For the Research stage specifically, evidence is
   grounded further still: before the AI drafts anything, ATLAS queries real
   paper sources (arXiv, Semantic Scholar, OpenAlex) and builds each
   evidence entry's citation and origin directly from that source's own
   metadata -- never from LLM recall. The AI's only role there is condensing
   an already-real abstract into a summary; it cannot invent sources.
2. **Presents it for human review** -- nothing is written to the project until
   you decide. Every proposal is also rendered to a plain-Markdown file under
   `atlas-proposals/pending/` in your project root -- readable and reviewable
   like any other file in your repo, not just as a JSON blob inside a
   dotfolder.
3. **Commits your decision.** Approve it and it becomes a permanent, versioned
   snapshot -- its Markdown record moves to `atlas-proposals/approved/` as a
   durable, git-diffable trail; reject it with feedback and regenerate.
4. **Extracts durable engineering knowledge** from what you approved, so later
   stages (and later projects) can draw on it.

The result is a project directory (`.atlas/`) holding a fully traceable history
of every research finding, planning decision, architectural choice, and
evaluation -- not just the final code, but the reasoning that produced it --
plus a repo-visible `atlas-proposals/` folder holding the human-readable record
of everything that was proposed and decided.

## Quick Start

### Prerequisites

- Python >= 3.12
- An API key for at least one supported AI provider (see
  [Configuring an AI Provider](#configuring-an-ai-provider))

### Install

```bash
pip install atlas-eng        # or: pipx install atlas-eng
```

Or try it without installing anything (needs [uv](https://github.com/astral-sh/uv)):

```bash
uvx atlas-eng demo
```

To install from source instead:

```bash
git clone https://github.com/sahil-mangla/atlas.git
cd atlas
pip install .
```

This installs the `atlas-eng` package, which provides the `atlas`
command and the `atlas_eng` Python package, in your active Python environment.

Support for some services is optional, so the base install stays small:

| Extra | Adds | Install |
|---|---|---|
| `gemini` | The `GEMINI` protocol (the default) | `pip install "atlas-eng[gemini]"` |
| `langfuse` | Sending traces to [Langfuse](https://langfuse.com) | `pip install "atlas-eng[langfuse]"` |
| `all` | Both | `pip install "atlas-eng[all]"` |

The `ANTHROPIC`, `OPENAI_COMPATIBLE`, `OLLAMA` and offline `SCRIPTED`
protocols need no extra.

```bash
atlas --version
# ATLAS  1.1.0
```

### See it work first (no API key)

```bash
atlas demo
```

This takes a throwaway project through every AI stage offline, using
built-in canned proposals instead of a model, and tells you where to find the
records it wrote. Nothing in your own workspace changes. See
[Testing Without an AI Provider](docs/testing.md).

### Configure

```bash
atlas init     # choose a provider; writes .env and asks for the API key
atlas doctor   # check the configuration; add --live to send one test request
```

`atlas init` never overwrites an existing `.env` unless you pass `--force`
(the old file is kept as `.env.bak`), and warns if `.env` is not git-ignored.
ATLAS reads `.env` from the current directory or any parent; environment
variables override it. See [Configuring an AI Provider](#configuring-an-ai-provider)
for every setting.

### Your First Project

```bash
# Create a project
atlas project create --name "My Project" \
  --description "A short description of what this is." \
  --objective "The core goal this project exists to achieve."

# The new project is now the current one, so --project-id can be left out
atlas workflow status

# Advance into the Research stage
atlas workflow transition --reason "Starting research."

# Generate an AI research proposal
atlas stage execute --stage research

# Review the generated proposal (printed above), then approve or reject it
atlas proposal approve --proposal-id <proposal-id>
# ...or, to send it back with feedback instead:
atlas proposal reject --proposal-id <proposal-id> \
  --feedback "Needs more evidence on X."
```

Wherever a command takes `--project-id`, you can give a project name
(`--project-id "My Project"`) or the start of its ID as shown by
`atlas project list`, or leave it out to use the current project. Switch the
current project with `atlas project use --project-id <name>`.

Repeat `stage execute` / `proposal approve` for each subsequent AI-assisted
stage (`planning`, `architecture`, `review`) as the project progresses. Once
the project reaches a human-driven stage with no AI executor (`iteration`,
`completion`), clear its listed objectives with `workflow complete-objective`
before running `workflow transition` again -- see [Progressing through a
human-driven stage](docs/architecture/workflow-stages.md#progressing-through-a-human-driven-stage).

Each committed stage proposal may also extract engineering-knowledge
candidates -- run `atlas knowledge list` to see them, `atlas knowledge show
--candidate-id <candidate-id>` for full detail, and `atlas knowledge approve` (publishes)
or `atlas knowledge reject --feedback <f>` to review one.

See the [CLI Reference](#cli-reference) below for the full command set.

## Configuring an AI Provider

ATLAS is provider-agnostic: it talks to any of four protocols through a common
interface (plus an offline `SCRIPTED` one for demos and tests), selected via `ATLAS_AI_PROTOCOL` (defaults to `GEMINI`). `.env.example`
has a ready-to-uncomment block for each row below, including OpenAI and
LM Studio (both are `OPENAI_COMPATIBLE` targets, not separate protocols).

| Protocol | Env var(s) | Notes |
|---|---|---|
| `GEMINI` | `ATLAS_GEMINI_API_KEY`, `ATLAS_GEMINI_MODEL` | Google's Gemini API. Default provider. Cloud. Needs the `gemini` extra. |
| `ANTHROPIC` | `ATLAS_AI_API_KEY`, `ATLAS_AI_MODEL` | Anthropic's Messages API. Cloud. |
| `OPENAI_COMPATIBLE` | `ATLAS_AI_API_KEY`, `ATLAS_AI_MODEL`, `ATLAS_AI_ENDPOINT` | OpenAI itself (cloud), or any OpenAI-compatible endpoint -- including [LM Studio](https://lmstudio.ai)'s local server (`http://localhost:1234/v1`, no API key needed). Give the base URL only -- ATLAS appends `/chat/completions` itself. Endpoint and model are both required; there is no default endpoint. |
| `SCRIPTED` | none | Offline, deterministic demo and test provider. Returns canned drafts; no key, no network. |
| `OLLAMA` | `ATLAS_AI_MODEL`, `ATLAS_AI_ENDPOINT` | Local models via [Ollama](https://ollama.com); no API key needed. Endpoint defaults to `http://localhost:11434`. |

All protocols also respect `ATLAS_AI_TIMEOUT_SECONDS` (default `60`, seconds)
for the HTTP request timeout. Cloud providers (Gemini, Anthropic, OpenAI)
rarely need more than the default. Locally-hosted models (Ollama, LM Studio)
generating long structured drafts on modest hardware can take well over a
minute -- if you see AI provider timeout errors against a local model, raise
this to `180`-`300`.

All settings are read as environment variables prefixed with `ATLAS_` (e.g.
`ATLAS_WORKSPACE_ROOT` to change where project directories are created,
default `./workspace`). Copy `.env.example` to `.env` and fill in your values
to configure a project directory instead of exporting variables by hand.

## Optional Features

- **Semantic knowledge retrieval:** rank published knowledge by relevance
  using an embedded vector index. See
  [Semantic Knowledge Retrieval](docs/semantic-retrieval.md).
- **Tracing:** every request is traced to `<workspace>/traces/`, and to
  [Langfuse](https://langfuse.com) with the `langfuse` extra and keys. See the
  [Observability Guide](docs/observability.md).
- **Evaluations:** a YAML benchmark suite, runnable offline or against a real
  model. See the [Evaluation Guide](docs/evaluations.md).

## CLI Reference

```
atlas <group> <sub-command> [flags]
```

| Group | Command | Description |
|---|---|---|
| `demo` | | Run the whole workflow offline on a throwaway project |
| `init` | `[--protocol <p>] [--model <m>] [--endpoint <url>] [--force]` | Write `.env` for an AI provider |
| `doctor` | `[--live]` | Check the configuration |
| `project` | `create --name <n> --description <d> --objective <o>` | Create a new project workspace |
| | `load` | Load a project's context |
| | `list` | List all known projects |
| | `archive` | Archive an active project |
| | `use --project-id <name\|id>` | Set the current project |
| `workflow` | `status` | Show the current stage and readiness |
| | `transition --reason <r>` | Transition to the next stage |
| | `complete-objective --objective <o>` | Clear one active objective on a human-driven stage (`problem_definition`, `implementation`, `iteration`, `completion`) |
| `stage` | `execute --stage <s>` | Generate an AI draft for the current stage |
| `proposal` | `approve --proposal-id <uuid>` | Approve and commit a draft |
| | `reject --proposal-id <uuid> --feedback <f>` | Reject a draft with feedback |
| `knowledge` | `list [--status <s>]` | List engineering-knowledge candidates |
| | `show --candidate-id <uuid>` | Show one candidate's full content |
| | `approve --candidate-id <uuid>` | Approve and publish a candidate (one step) |
| | `reject --candidate-id <uuid> --feedback <f>` | Reject a candidate with feedback |
| `presentation` | `dashboard\|workflow\|research\|knowledge\|diagnostics [--format <f>]` | Render a composed view to stdout |
| | `export --view <v> --output <path> [--format <f>]` | Render a view to a file |

Commands that act on a project take `--project-id <name|id>`; leave it out
to use the current project. `<s>` is one of `research`, `planning`,
`architecture`, `review`. `<f>` (presentation format) is one of `cli` (default), `markdown`, `json`. Full details:
[docs/usage/cli.md](docs/usage/cli.md).

## Architecture

ATLAS is a strict layered system under one package, `atlas_eng`: a stateless
domain and engineering core (`engine/`), a versioned public SDK at the top
level, a presentation layer that renders read models, and thin clients (the
CLI today). See the [Package Map](docs/architecture/package-map.md) and the
[System Overview](docs/architecture/system-overview.md).

## Documentation

The full architecture reference, ADRs, and diagrams live under
[`docs/`](docs/README.md):

- [Architecture Documentation Index](docs/README.md) -- the complete reference
- [CLI Usage Guide](docs/usage/cli.md)
- [System Overview](docs/architecture/system-overview.md)
- [Engineering Workflow](docs/architecture/engineering-workflow.md)
- [Architecture Decision Records](docs/decisions)
- [Glossary](docs/glossary.md)
- [Observability Guide](docs/observability.md)
- [Evaluation and Regression Guide](docs/evaluations.md)
- [Testing Without an AI Provider](docs/testing.md)
- [Project History](docs/history/README.md) -- original blueprint, phase plans and sprint reports
- [CHANGELOG](CHANGELOG.md)

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md)
for setup, checks and where code goes, and [SECURITY.md](SECURITY.md) to
report a vulnerability privately.

## License

[MIT](LICENSE)

## Project Status

ATLAS is at **v1.1.0**, distributed as `atlas-eng`, following the completion
of all sixteen planned phases (see [`CHANGELOG.md`](CHANGELOG.md) and
[`docs/history/reports/`](docs/history/reports) for the full history, including the
seven-sprint Phase 16 production-readiness pass). Version 2 scope -- additional client adapters (MCP, REST, IDE)
and the performance-review candidates documented in
[`docs/history/reports/phase-16-sprint-6-performance-review.md`](docs/history/reports/phase-16-sprint-6-performance-review.md)
-- is not yet started.
