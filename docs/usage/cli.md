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
- `atlas workflow status --project-id <uuid>`: Show the current stage and readiness.
- `atlas workflow transition --project-id <uuid> --reason <r>`: Transition to the next stage.

#### `stage`
Execute active stages.
- `atlas stage execute --project-id <uuid> --stage <s>`: Start AI generation for the current stage.

#### `proposal`
Review AI-generated drafts.
- `atlas proposal approve --project-id <uuid> --proposal-id <uuid>`: Approve and commit a draft.
- `atlas proposal reject --project-id <uuid> --proposal-id <uuid> --feedback <f>`: Reject a draft and provide feedback.

## Configuration
The CLI adapts to the terminal's width and detected Unicode support automatically. No extra configuration is needed.
