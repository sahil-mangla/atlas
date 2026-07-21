# ATLAS

**Where Ideas Become Engineering.**

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/sahil-mangla/atlas/blob/main/CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/downloads/)
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
- [CLI Reference](#cli-reference)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [Development Setup](#development-setup)
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
   architecture decisions).
2. **Presents it for human review** -- nothing is written to the project until
   you decide.
3. **Commits your decision.** Approve it and it becomes a permanent, versioned
   snapshot; reject it with feedback and regenerate.
4. **Extracts durable engineering knowledge** from what you approved, so later
   stages (and later projects) can draw on it.

The result is a project directory (`.atlas/`) holding a fully traceable history
of every research finding, planning decision, architectural choice, and
evaluation -- not just the final code, but the reasoning that produced it.

## Quick Start

### Prerequisites

- Python >= 3.13
- An API key for at least one supported AI provider (see
  [Configuring an AI Provider](#configuring-an-ai-provider))

### Install

**From source (recommended until a PyPI release is published):**

```bash
git clone https://github.com/sahil-mangla/atlas.git
cd atlas
pip install .
```

**Directly from GitHub, without cloning:**

```bash
pip install git+https://github.com/sahil-mangla/atlas.git
```

Either way, this installs the `atlas` command globally in your active Python
environment.

```bash
atlas version
# ATLAS  1.0.0
```

### Configure

ATLAS reads configuration from environment variables (optionally via a `.env`
file in your working directory). At minimum, set an API key for your chosen
provider -- see [Configuring an AI Provider](#configuring-an-ai-provider) below.

```bash
export ATLAS_GEMINI_API_KEY="your-api-key-here"
```

### Your First Project

```bash
# Create a project
atlas project create --name "My Project" \
  --description "A short description of what this is." \
  --objective "The core goal this project exists to achieve."

# Note the project ID printed above, then check its status
atlas workflow status --project-id <project-id>

# Advance into the Research stage
atlas workflow transition --project-id <project-id> --reason "Starting research."

# Generate an AI research proposal
atlas stage execute --project-id <project-id> --stage research

# Review the generated proposal (printed above), then approve or reject it
atlas proposal approve --project-id <project-id> --proposal-id <proposal-id>
# ...or, to send it back with feedback instead:
atlas proposal reject --project-id <project-id> --proposal-id <proposal-id> \
  --feedback "Needs more evidence on X."
```

Repeat `stage execute` / `proposal approve` for each subsequent stage
(`planning`, `architecture`, `review`) as the project progresses. See the
[CLI Reference](#cli-reference) below for the full command set.

## Configuring an AI Provider

ATLAS is provider-agnostic: it talks to any of four protocols through a common
interface, selected via `ATLAS_AI_PROTOCOL` (defaults to `GEMINI`).

| Protocol | Env var(s) | Notes |
|---|---|---|
| `GEMINI` | `ATLAS_GEMINI_API_KEY`, `ATLAS_GEMINI_MODEL` | Google's Gemini API. Default provider. |
| `ANTHROPIC` | `ATLAS_AI_API_KEY`, `ATLAS_AI_MODEL` | Anthropic's Messages API. |
| `OPENAI_COMPATIBLE` | `ATLAS_AI_API_KEY`, `ATLAS_AI_MODEL`, `ATLAS_AI_ENDPOINT` | Any OpenAI-compatible chat completions endpoint. |
| `OLLAMA` | `ATLAS_AI_MODEL`, `ATLAS_AI_ENDPOINT` | Local models via Ollama; no API key needed. |

All protocols also respect `ATLAS_AI_TIMEOUT_SECONDS` (default `60`) for
the HTTP request timeout. Locally-hosted models generating long
structured drafts may need this raised well above the default.

All settings are read as environment variables prefixed with `ATLAS_` (e.g.
`ATLAS_WORKSPACE_ROOT` to change where project directories are created,
default `./workspace`). Copy `.env.example` to `.env` and fill in your values
to configure a project directory instead of exporting variables by hand.

## CLI Reference

```
atlas <group> <sub-command> [flags]
```

| Group | Command | Description |
|---|---|---|
| `project` | `create --name <n> --description <d> --objective <o>` | Create a new project workspace |
| | `load --project-id <uuid>` | Load a project's context |
| | `list` | List all known projects |
| | `archive --project-id <uuid>` | Archive an active project |
| `workflow` | `status --project-id <uuid>` | Show the current stage and readiness |
| | `transition --project-id <uuid> --reason <r>` | Transition to the next stage |
| `stage` | `execute --project-id <uuid> --stage <s>` | Generate an AI draft for the current stage |
| `proposal` | `approve --project-id <uuid> --proposal-id <uuid>` | Approve and commit a draft |
| | `reject --project-id <uuid> --proposal-id <uuid> --feedback <f>` | Reject a draft with feedback |

`<s>` is one of `research`, `planning`, `architecture`, `review`. Full details:
[docs/usage/cli.md](docs/usage/cli.md).

## Architecture

ATLAS is organized as a strict layered architecture: a stateless, protocol-
independent domain and engineering core (`engine/`), a versioned public SDK
boundary (`atlas/`), a presentation layer that renders read models without
touching engine internals (`presentation/`), and thin client adapters
(`clients/`) that translate an external environment (CLI today; MCP, REST,
and IDE integrations are Version 2 scope) into calls against that SDK.

- **`atlas/`** -- Public Application Platform SDK exposing the `Atlas` facade,
  immutable command/result DTOs, and application exceptions.
  - **`atlas/capabilities/`** -- Internal Capability Layer decomposing `Atlas`
    into five thin delegation classes -- Project, Workflow, WorkflowExecution,
    Knowledge, Presentation.
  - **`atlas/contracts/`** -- Public Contract Layer -- versioned
    `RequestEnvelope`/`ResponseEnvelope`, the `PlatformErrorCode` error
    contract, and API versioning.
  - **`atlas/adapters/`** -- Public Adapter Boundary -- the structural
    `PlatformAdapter` protocol and capability-negotiation manifest every
    client (CLI, IDE, MCP, AI, REST, Desktop) satisfies.
- **`engine/domain/`** -- Strongly-typed, framework-independent Pydantic
  models representing the ubiquitous domain language of ATLAS, including the
  Engineering Design Language (EDL) components (`TraceabilityLink`,
  `ArtifactMetadata` composition, `EngineeringReview` contracts), AI proposal
  drafts (`ai_drafts.py`), and review feedback (`ai_feedback.py`).
- **`engine/project/`** -- Project Subsystem: workspace initialization
  (`.atlas/`), loading, metadata discovery, and lifecycle states (initialized,
  active, paused, archived).
- **`engine/memory/`** -- Memory Subsystem managing dialogue context and
  history.
- **`engine/knowledge/`** -- Knowledge Subsystem: the Engineering Knowledge
  Layer collecting, deduplicating, retrieving, and managing reviewed
  project-scoped engineering knowledge.
- **`engine/workflow/`** -- Workflow Subsystem: execution readiness, phase
  transitions, and lifecycle orchestration.
- **`engine/research/`** -- Research Subsystem: problem definition, evidence
  gathering, snapshotting, hypothesis validation.
- **`engine/planning/`** -- Planning Subsystem: decomposing research into
  scopes, milestones, epics, tasks, subtasks, and dependencies.
- **`engine/architecture/`** -- Architecture Subsystem: component modeling,
  architectural decisions, interface contracts, and risk analysis.
- **`engine/evaluation/`** -- Evaluation Subsystem: readiness review and
  stage-completion evaluation.
- **`engine/ai/`** -- AI Integration Subsystem: protocol adapters (Gemini,
  Anthropic, OpenAI-compatible, Ollama), context assembly, orchestration, and
  stateless engineering proposal services.
- **`presentation/`** -- Presentation Layer: composes typed, immutable Views
  from the Atlas read-model API and renders them to JSON/Markdown/CLI,
  independent of any client adapter.
- **`clients/`** -- Client adapters (CLI today; MCP/IDE/REST are Version 2)
  translating external execution environments to the public Atlas SDK.
- **`shared/`** -- Common utilities and cross-cutting concerns.

## Documentation

The full architecture reference, ADRs, and diagrams live under
[`docs/`](docs/README.md):

- [Architecture Documentation Index](docs/README.md) -- the complete reference
- [CLI Usage Guide](docs/usage/cli.md)
- [System Overview](docs/architecture/system-overview.md)
- [Engineering Workflow](docs/architecture/engineering-workflow.md)
- [Architecture Decision Records](docs/decisions/)
- [Glossary](docs/glossary.md)
- [CHANGELOG](CHANGELOG.md)

## Development Setup

ATLAS uses [uv](https://github.com/astral-sh/uv) for fast, reproducible
package and dependency management during development.

### Prerequisites

- Python >= 3.13
- uv

### Installation

```bash
git clone https://github.com/sahil-mangla/atlas.git
cd atlas
uv sync
cp .env.example .env
```

### Local Development Workflow

Three tools are pre-configured for code quality:

- **Ruff** -- formatting and linting
- **mypy** -- strict static type checking
- **pytest** -- automated testing and coverage

```bash
# Lint and format
uv run ruff check . --fix
uv run ruff format .

# Type check
uv run mypy .

# Test
uv run pytest
```

### Pre-commit Hooks

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

### Continuous Integration

Every push and pull request against `main` runs the full verification suite
(`ruff check`, `ruff format --check`, `mypy`, `pytest`) via
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Contributing

Issues and pull requests are welcome:

- **Bug reports / feature requests:** use the templates under
  [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/).
- **Pull requests:** follow the checklist in
  [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) --
  run `pytest`, `mypy`, and `ruff` locally before opening one.

## License

[MIT](LICENSE)

## Project Status

ATLAS is at **v1.0.0** -- the first tagged release, following the completion
of all sixteen planned phases (see [`CHANGELOG.md`](CHANGELOG.md) and
[`docs/reports/`](docs/reports/) for the full history, including the
seven-sprint Phase 16 production-readiness pass). Version 2 scope --
additional client adapters (MCP, REST, IDE), a published PyPI package, and
the performance-review candidates documented in
[`docs/reports/phase-16-sprint-6-performance-review.md`](docs/reports/phase-16-sprint-6-performance-review.md)
-- is not yet started.
