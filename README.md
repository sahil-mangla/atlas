# ATLAS

## Where Ideas Become Engineering.

ATLAS is an AI-native engineering operating system that transforms ideas into production-ready software through structured research, architecture, planning, implementation, verification, and persistent project intelligence.

---

## Package Structure

- **`engine/domain/`**: Strongly-typed, framework-independent Pydantic models representing the ubiquitous domain language of ATLAS (Projects, Workspace, Research, Roadmaps, etc.).
- **`engine/project/`**: Project Subsystem governing workspace initialization (`.atlas/`), loading, metadata discovery, and lifecycle states (initialized, active, paused, archived).
- **`interfaces/`**: External adapters and entry points (CLI, API) — *Reserved for future stages*.
- **`shared/`**: Common utilities and shared cross-cutting concerns.

---

## Development Setup

ATLAS uses [uv](https://github.com/astral-sh/uv) for fast, robust package and dependency management.

### Prerequisites

- Python >= 3.13
- uv

### Installation

Clone the repository and run `uv sync` to set up the virtual environment and install all dependencies:

```bash
# Sync dependencies and set up virtual environment
uv sync
```

Copy the environment variables template to create your local configurations:

```bash
cp .env.example .env
```

### Local Development Workflow

To ensure high code quality, several tools are pre-configured:
- **Ruff**: For formatting and linting.
- **mypy**: For strict static type checking.
- **pytest**: For automated unit testing and coverage.

#### Code Formatting & Linting

```bash
# Run Ruff lint check
uv run ruff check . --fix

# Run Ruff format check
uv run ruff format .
```

#### Type Checking

```bash
# Run mypy type checking
uv run mypy .
```

#### Testing Workflow

```bash
# Run tests with pytest
uv run pytest
```

### Pre-commit Hooks

Ensure pre-commit hooks are installed before making commits. They will automatically run linting, formatting, and type-checks on staged files:

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run all hooks manually on all files
uv run pre-commit run --all-files
```
