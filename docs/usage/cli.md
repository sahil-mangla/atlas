# ATLAS CLI Usage Guide

The ATLAS CLI provides a command-line interface to the underlying ATLAS engineering platform.

## Installation

When the `atlas-eng` package is installed, the CLI is available globally:

```bash
atlas --version
atlas --help        # also: atlas help, atlas <group> --help
```

## Getting Started

These three commands work before any configuration exists, and while it is
broken; none of them starts the platform with your settings.

- `atlas demo`: Take a throwaway project through every AI stage offline, using
  built-in canned proposals (no model, no key, no network), in a temporary
  directory. Prints where the records were written.
- `atlas init [--protocol <p>] [--model <m>] [--endpoint <url>] [--force]`:
  Write `.env` in the current directory for one AI protocol. Asks for anything
  the flags do not supply; API keys are only ever read from a hidden prompt,
  never from flags. Without a terminal, pass `--protocol`; unanswered values
  are left commented out. Refuses to replace an existing `.env` unless
  `--force` is given, and then keeps the old file as `.env.bak`. Warns when
  `.env` is not ignored by git.
- `atlas doctor [--live]`: Check the configuration: which `.env` was found,
  the protocol and its required settings, whether its optional package is
  installed, the workspace, semantic retrieval and Langfuse. Each problem
  comes with the fix. Exits 1 if any check fails. `--live` also sends one
  small request to the configured model (this may cost a few tokens).

## Usage

```bash
atlas <group> <sub-command> [flags]
```

### Flag Syntax

- Both `--flag value` and `--flag=value` are accepted for every flag.
- Each flag may be specified once per command. Repeating a flag (e.g. two
  `--name` values) raises a parse error rather than silently keeping only
  the last one.
- A flag given without a value (e.g. immediately followed by another flag)
  raises a parse error naming the flag that needs a value, rather than
  silently consuming the next flag's name as this flag's value.
- On/off switches (`--force`, `--live`) take no value.

### Available Groups

#### `project`
Manage project lifecycles.
- `atlas project create --name <n> --description <d> --objective <o>`: Create a new project workspace.
- `atlas project load --project-id <uuid>`: Load a project context into active memory.
- `atlas project list`: List all known projects.
- `atlas project archive --project-id <uuid>`: Archive an active project.

#### `workflow`
Manage workflow progress.
- `atlas workflow status --project-id <uuid>`: Show the current stage, readiness, and active objectives.
- `atlas workflow transition --project-id <uuid> --reason <r>`: Transition to the next stage. Blocked until every active objective is cleared.
- `atlas workflow complete-objective --project-id <uuid> --objective <o>`: Clear one active objective. This is the only way to progress through a human-driven stage that has no AI executor (`problem_definition`, `implementation`, `iteration`, `completion`) -- see [Progressing through a human-driven stage](../architecture/workflow-stages.md#progressing-through-a-human-driven-stage).

#### `stage`
Execute active stages.
- `atlas stage execute --project-id <uuid> --stage <s>`: Start AI generation for the current stage.

#### `proposal`
Review AI-generated drafts. Each generated proposal is also written as
Markdown to `atlas-proposals/pending/<proposal-id>.md` in the project root --
read it there instead of the underlying `.atlas/proposals/<id>.json`.
- `atlas proposal approve --project-id <uuid> --proposal-id <uuid>`: Approve and commit a draft. Its Markdown file moves to `atlas-proposals/approved/`.
- `atlas proposal reject --project-id <uuid> --proposal-id <uuid> --feedback <f>`: Reject a draft and provide feedback.

#### `knowledge`
List and review engineering-knowledge candidates extracted from committed stage proposals.
- `atlas knowledge list --project-id <uuid> [--status <s>]`: List candidates, optionally filtered by status (`pending_review`, `approved`, `rejected`, `withdrawn`).
- `atlas knowledge show --project-id <uuid> --candidate-id <uuid>`: Show one candidate's full content.
- `atlas knowledge approve --project-id <uuid> --candidate-id <uuid> [--feedback <f>] [--actor <a>]`: Approve a candidate. This publishes it in the same step -- there is no separate publish command.
- `atlas knowledge reject --project-id <uuid> --candidate-id <uuid> --feedback <f> [--actor <a>]`: Reject a candidate with required feedback.

#### `presentation`
Render composed presentation views (Phase 14 typed views) for a project.
- `atlas presentation dashboard --project-id <uuid> [--format <f>]`: Project dashboard.
- `atlas presentation workflow --project-id <uuid> [--format <f>]`: Workflow status view.
- `atlas presentation research --project-id <uuid> [--format <f>]`: Research summary view.
- `atlas presentation knowledge --project-id <uuid> [--format <f>]`: Knowledge summary view.
- `atlas presentation diagnostics --project-id <uuid> [--format <f>]`: Diagnostics view.
- `atlas presentation export --project-id <uuid> --view <v> --output <path> [--format <f>]`: Render any of the above views to a file instead of stdout.

`<f>` is one of `cli` (default, terminal-friendly plain text), `markdown`, or `json`. `<v>` is one of `dashboard`, `workflow`, `research`, `knowledge`, `diagnostics`. All rendering is delegated to `Atlas.render`/`RendererRegistry` -- the CLI does no formatting of its own.

## Configuration
The CLI adapts to the terminal's width and detected Unicode support automatically. No extra configuration is needed.
