# ATLAS CLI Usage Guide

The ATLAS CLI provides a command-line interface to the underlying ATLAS engineering platform.

## Installation

When the `atlas` package is installed, the CLI is available globally:

```bash
atlas version
```

## Usage

```bash
atlas <group> <sub-command> [flags]
```

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
Review AI-generated drafts.
- `atlas proposal approve --project-id <uuid> --proposal-id <uuid>`: Approve and commit a draft.
- `atlas proposal reject --project-id <uuid> --proposal-id <uuid> --feedback <f>`: Reject a draft and provide feedback.

#### `knowledge`
List and review engineering-knowledge candidates extracted from committed stage proposals.
- `atlas knowledge list --project-id <uuid> [--status <s>]`: List candidates, optionally filtered by status (`pending_review`, `approved`, `rejected`, `withdrawn`).
- `atlas knowledge show --project-id <uuid> --candidate-id <uuid>`: Show one candidate's full content.
- `atlas knowledge approve --project-id <uuid> --candidate-id <uuid> [--feedback <f>] [--actor <a>]`: Approve a candidate. This publishes it in the same step -- there is no separate publish command.
- `atlas knowledge reject --project-id <uuid> --candidate-id <uuid> --feedback <f> [--actor <a>]`: Reject a candidate with required feedback.

## Configuration
The CLI adapts to the terminal's width and detected Unicode support automatically. No extra configuration is needed.
