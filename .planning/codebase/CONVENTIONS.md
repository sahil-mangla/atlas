# Coding Conventions

**Analysis Date:** 2026-07-19

## Naming Patterns

**Files:**
- Service files: `[subsystem]/services.py` (e.g., `engine/research/services.py`)
- Repository files: `[subsystem]/repository.py` (interface) and `[subsystem]/fs_repository.py` (filesystem impl)
- Exception files: `[subsystem]/exceptions.py`
- Serializer files: `[subsystem]/serializers.py`
- Domain models: `engine/domain/[entity].py` (e.g., `engine/domain/research.py`)
- Test files: `tests/[subsystem]/test_[module].py` - mirror source structure exactly

**Functions:**
- All lowercase with snake_case: `initialize_research()`, `add_source()`, `get_by_project_id()`
- Getter functions use simple names or follow Pydantic conventions: `get_settings()`
- Private methods prefixed with single underscore: `_ensure_mutable()`, `_validate_state()`
- Service methods are typically public (no underscore prefix)

**Variables:**
- Local variables: snake_case: `project_id`, `research_snapshot`, `artifact_metadata`
- Constants: UPPER_SNAKE_CASE (if used)
- Boolean prefixes: `is_`, `has_`, `can_`: `is_active`, `has_entries`, `can_modify`
- Type hints always present: `project_id: UUID`, `entries: list[str]`

**Types:**
- Classes: PascalCase: `Research`, `ResearchSource`, `FilesystemResearchRepository`
- Exception classes: PascalCase ending in `Exception`: `ResearchNotFoundException`, `InvalidResearchOperationException`
- Enum classes: PascalCase: `Environment`, `ResearchStatus`, `MemoryCategory`
- Union types use `|` syntax (Python 3.10+): `Memory | None`, `list[str] | None`

## Code Style

**Formatting:**
- Line length: 88 characters (Ruff default)
- Python version: 3.13+
- Formatter: Ruff format (`ruff-format`)

**Linting:**
- Tool: Ruff with strict rule set
- Active rules: E, W, F, I (isort), N (PEP8-naming), UP, B, A, C4, T20, RET, SIM, ARG, PTH, ERA, PL, RUF
- No ignored rules
- Docstring convention: Google-style (enforced by pydocstyle)
- Pre-commit hook: `ruff check --fix` and `ruff format` run automatically

**Type Checking:**
- Tool: mypy in strict mode (`mypy --strict`)
- Strict settings enabled: no implicit `Any`, all functions must have return types
- Exclusions: `.venv/` directory
- Pre-commit hook: mypy runs with `--strict` flag

## Import Organization

**Order:**
1. Standard library imports (e.g., `from uuid import UUID`, `from pathlib import Path`)
2. Third-party imports (e.g., `from pydantic import BaseModel`, `from google.genai import Client`)
3. Local imports (e.g., `from engine.domain.research import Research`)

**Path Aliases:**
- None configured - all imports use absolute paths
- Imports always relative to project root: `from engine.config import Settings`

**isort/Ruff-import integration:**
- Ruff's "I" rule enforces import ordering automatically
- Pre-commit hook runs `ruff check --fix` to auto-order imports

## Error Handling

**Patterns:**
- Custom exception hierarchy per subsystem: base class in `[subsystem]/exceptions.py`
- Example hierarchy (Research):
  ```python
  class ResearchException(Exception):
      """Base exception for Research subsystem errors."""
  
  class ResearchNotFoundException(ResearchException):
      """Raised when research for a project cannot be found."""
  
  class InvalidResearchOperationException(ResearchException):
      """Raised when an operation violates research business rules."""
  ```
- Services raise exceptions rather than returning error codes
- Exceptions include descriptive messages: `raise InvalidResearchOperationException(f"Research already exists for project {project_id}.")`
- No try/except in service layer - exceptions propagate to caller
- Validation happens at entry points via business rule checks

## Logging

**Framework:** Not implemented in service layer

**Patterns:**
- No explicit logging in business logic (`engine/` layer)
- Debug flag available in settings: `settings.debug`
- Logging configuration available via `log_level` setting (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- CLI layer handles output via `capsys` or stdout (as seen in CLI tests)

## Comments

**When to Comment:**
- Docstrings on all public functions and classes (required for passing linting)
- Business logic explanation for complex algorithms
- Rationale for non-obvious design decisions
- Avoid comments that duplicate what code says

**JSDoc/TSDoc:**
- Not used (Python project)
- Google-style docstrings required via pydocstyle
- Example:
  ```python
  def initialize_research(
      self, project_id: UUID, problem_statement: str, objectives: list[str]
  ) -> Research:
      """Create a new research context for a project.
      
      Args:
          project_id: The UUID of the project.
          problem_statement: The initial problem definition.
          objectives: List of research objectives.
      
      Returns:
          The initialized Research aggregate.
      
      Raises:
          InvalidResearchOperationException: If research already exists.
      """
  ```

## Function Design

**Size:** Keep functions focused on single responsibility

**Parameters:**
- Always use type hints: `def add_source(self, project_id: UUID, title: str, url: str)`
- Prefer keyword arguments for clarity in service methods
- Avoid boolean parameters without naming: use `is_active: bool` not just `active: bool`
- Use `| None` for optional types instead of `Optional[]`

**Return Values:**
- Always include explicit return type hints: `-> Research`, `-> None`, `-> list[UUID]`
- Return custom domain objects, not raw dicts
- Return the aggregate after modification for method chaining capability

## Module Design

**Exports:**
- Services are main exports from a subsystem
- Repositories are injected, not directly imported by consumers
- Exceptions exported from subsystem `__init__.py` for convenience

**Barrel Files:**
- Used in some modules: `engine/research/__init__.py` may re-export common types
- Not universally applied - check each module's `__init__.py`

## Pydantic Models (Domain Objects)

**Field definitions:**
- All fields include `Field()` with description: 
  ```python
  statement: str = Field(description="Detailed description of the problem.")
  ```
- UUID fields use `Field(default_factory=uuid4, ...)` for auto-generation
- Datetime fields use `Field(default_factory=lambda: datetime.now(UTC), ...)`
- List fields use `default_factory=list` not mutable default
- Validation rules in Field (e.g., `min_length=1`)

**Inheritance:**
- Domain models inherit from `pydantic.BaseModel`
- Settings inherit from `pydantic_settings.BaseSettings`
- Custom field validators using Pydantic v2 `@field_validator` if needed

## Subsystem Structure

All subsystems in `engine/` follow this pattern:

```
engine/[subsystem]/
├── __init__.py          # Exports public API
├── repository.py        # Abstract repository interface
├── fs_repository.py     # Filesystem implementation
├── services.py          # Business logic services
├── serializers.py       # JSON/storage serialization
└── exceptions.py        # Subsystem-specific exceptions
```

Each subsystem is independently testable with matching test directory:
```
tests/[subsystem]/
├── test_repository.py
├── test_services.py
├── test_serializers.py
└── test_exceptions.py
```

---

*Convention analysis: 2026-07-19*
