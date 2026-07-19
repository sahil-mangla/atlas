# Technology Stack

**Analysis Date:** 2026-07-19

## Languages

**Primary:**
- Python 3.13+ - All core platform, subsystems, and engine logic

## Runtime

**Environment:**
- Python 3.13+ via system python or virtual environment

**Package Manager:**
- uv (unified Python package installer)
- Lockfile: `uv.lock` managed by uv (not included in git)

## Frameworks

**Core:**
- No web framework (event-driven CLI and daemon-capable architecture)

**Configuration:**
- Pydantic 2.7+ - Data validation and settings management
- Pydantic Settings 2.2+ - Environment-based configuration (see `engine/config.py`)

**Testing:**
- pytest 8.0+ - Test runner and framework
- pytest-cov 4.1+ - Coverage reporting

**Build/Dev:**
- hatchling - Python package builder
- ruff 0.4+ - Code formatting and linting (configured in `pyproject.toml`)
- mypy 1.9+ - Strict static type checking
- pre-commit 3.6+ - Git hook automation

## Key Dependencies

**Critical:**
- google-genai 1.0+ - Google Gemini AI model access (primary AI provider)
- pydantic 2.7+ - Domain model validation and type enforcement across `engine/domain/`

**Infrastructure:**
- None (uses Python standard library only for HTTP: `urllib` in `engine/ai/adapters/_http.py`)

## Configuration

**Environment:**
- `.env` file (created from `.env.example` template)
- Environment variables prefixed with `ATLAS_`
- Configuration loaded via Pydantic Settings in `engine/config.py`

**Required settings:**
- `ATLAS_GEMINI_API_KEY` - API credential for Google Gemini provider
- `ATLAS_GEMINI_MODEL` - Gemini model identifier (e.g., `gemini-2.0-flash`)
- `ATLAS_ENVIRONMENT` - Execution context: `development`, `testing`, or `production`
- `ATLAS_WORKSPACE_ROOT` - Filesystem path to active workspace (default: `./workspace`)

**Optional settings:**
- `ATLAS_DEBUG` - Enable verbose logging (default: `false`)
- `ATLAS_LOG_LEVEL` - Logging verbosity (default: `INFO`)
- `ATLAS_AI_PROTOCOL` - AI provider protocol override
- `ATLAS_AI_ENDPOINT` - Custom AI provider endpoint
- `ATLAS_AI_MODEL` - Alternative model identifier
- `ATLAS_AI_API_KEY` - Alternative provider credential

**Build:**
- `pyproject.toml` - Package metadata, dependencies, build config, and tool configuration
- `tsconfig.json` - Not used (Python-only project)

## Platform Requirements

**Development:**
- Python 3.13+ installed
- uv package manager
- UNIX-like shell (zsh/bash preferred)
- Pre-commit hook support (git 2.0+)

**Production:**
- Python 3.13+ runtime
- Google Genai API credential (API key)
- Filesystem write access for `.atlas/` workspace directory

## Testing Configuration

**Test Runner:**
- pytest (configured in `pyproject.toml` under `[tool.pytest.ini_options]`)
- Test discovery: `tests/` directory
- Coverage: Enabled for `engine/`, `interfaces/`, `shared/`, `clients/` packages
- Command: `uv run pytest` or `pytest`

**Code Quality Tools:**

Configured in `pyproject.toml`:

| Tool | Purpose | Config |
|------|---------|--------|
| ruff | Formatting & linting | Line length 88, target Python 3.13 |
| mypy | Type checking | Strict mode enabled |
| pre-commit | Git hooks | Configured in `.pre-commit-config.yaml` |

**Development Workflow:**
```bash
uv sync                          # Install dependencies
uv run ruff check . --fix        # Lint with auto-fix
uv run ruff format .             # Format code
uv run mypy .                    # Type check
uv run pytest                    # Run tests with coverage
uv run pre-commit run --all-files # Run all pre-commit hooks
```

---

*Stack analysis: 2026-07-19*
