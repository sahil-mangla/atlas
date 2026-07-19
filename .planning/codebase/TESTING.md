# Testing Patterns

**Analysis Date:** 2026-07-19

## Test Framework

**Runner:**
- pytest 8.0.0+
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Assertion Library:**
- Built-in `assert` statements
- pytest's `pytest.raises()` for exception testing

**Run Commands:**
```bash
pytest                                          # Run all tests
pytest --cov=engine --cov=interfaces --cov=shared --cov=clients --cov-report=term-missing --cov-report=xml
                                               # Run with coverage report
pytest -v                                       # Verbose output
pytest tests/research/                         # Run specific module tests
pytest -k "test_initialization"                # Run tests matching pattern
```

## Test File Organization

**Location:**
- Co-located with source: `tests/[subsystem]/test_[module].py` mirrors `engine/[subsystem]/[module].py`
- Example: tests for `engine/research/services.py` live in `tests/research/test_services.py`

**Naming:**
- Test files: `test_*.py` (standard pytest convention)
- Test functions: `test_<feature>()` - descriptive name of what's tested
- Test classes: Not used - all test functions at module level

**Structure:**
```
tests/
├── conftest.py                    # Shared fixtures
├── [subsystem]/
│   ├── __init__.py
│   ├── test_repository.py         # Repository tests
│   ├── test_services.py           # Service logic tests
│   ├── test_serializers.py        # Serialization tests
│   ├── test_exceptions.py         # Exception behavior tests
│   └── test_[feature].py          # Feature-specific tests
├── test_config.py                 # Settings/config tests
├── support/                       # Test utilities
│   ├── test_bootstrap.py          # Platform assembly for integration tests
│   └── __init__.py
└── ai/
    └── test_adapters.py           # Mock implementations (e.g., MockAIProvider)
```

## Test Structure

**Suite Organization:**

Tests follow a flat structure with fixtures providing setup:

```python
"""Unit tests for the Research subsystem services.

S-03: FilesystemResearchRepository now requires a registered project. Each
test creates a project in the project repo before operating on research.
"""

from uuid import UUID, uuid4
import pytest

from engine.domain.research import Research
from engine.research.services import ResearchInitializationService
from engine.research.exceptions import InvalidResearchOperationException
from engine.research.fs_repository import FilesystemResearchRepository


@pytest.fixture
def setup(tmp_path: Path) -> tuple[FilesystemResearchRepository, UUID]:
    """Provide a repo and a registered project ID for service tests."""
    project_repo = FilesystemProjectRepository(tmp_path)
    repo = FilesystemResearchRepository(project_repo)
    
    project = Project(name="Test", description="d", objective="o")
    project_repo.save(project)
    
    return repo, project.id


def test_initialization_service(
    setup: tuple[FilesystemResearchRepository, UUID],
) -> None:
    """Verify initialization creates research in DRAFT state."""
    repo, project_id = setup
    svc = ResearchInitializationService(repo)
    
    research = svc.initialize_research(project_id, "Problem", ["Obj 1"])
    
    assert research.project_id == project_id
    assert research.status == ResearchStatus.DRAFT
```

**Patterns:**
- Module-level docstring explains test purpose and any architectural notes
- Fixtures provide test dependencies (repositories, mock objects)
- Each test function focuses on one behavior
- Descriptive test names match docstring
- Type hints on fixture returns and function parameters

## Mocking

**Framework:** `unittest.mock` (Python standard library)

**Patterns:**

Fake implementations for repositories (preferred for unit tests):
```python
class FakeMemoryRepository(MemoryRepository):
    def __init__(self) -> None:
        self.memories: dict[str, Memory] = {}
    
    def save(self, memory: Memory) -> None:
        self.memories[str(memory.project_id)] = memory
    
    def get_by_project_id(self, project_id: UUID) -> Memory | None:
        return self.memories.get(str(project_id))
```

MagicMock for CLI/interface layer tests:
```python
from unittest.mock import MagicMock, patch

def test_cli_app_run_ok() -> None:
    mock_atlas = MagicMock()
    mock_atlas.create_project.return_value = ProjectResult(...)
    
    app = CLIApplication(atlas_platform=mock_atlas)
    code = app.run(["project", "create", "--name", "Test"])
    
    assert code == _EXIT_OK
    mock_atlas.create_project.assert_called_once()
```

Patch for system calls and module-level functions:
```python
from unittest.mock import patch

@patch("sys.exit")
def test_main(mock_exit: MagicMock) -> None:
    with patch("clients.cli.application.atlas.create", return_value=MagicMock()):
        main(["version"])
        mock_exit.assert_called_once_with(_EXIT_OK)
```

**What to Mock:**
- External services (AI providers, APIs)
- System calls (sys.exit, os.environ)
- CLI platform object when testing CLI
- Large dependencies in integration test setups

**What NOT to Mock:**
- Domain objects (Research, Memory, etc.)
- Repositories when testing service logic (use Fakes instead)
- Business logic - test the actual service methods
- Exceptions - let them be raised naturally

## Fixtures and Factories

**Test Data:**

Helper functions for creating test data:
```python
def create_snapshot(snapshot_id: UUID) -> ResearchSnapshot:
    return ResearchSnapshot(
        metadata=ArtifactMetadata(id=snapshot_id, version=1),
        problem_definition=ProblemDefinition(statement="A", objectives=[]),
        research_sources=[],
        evidence=[],
        findings=[],
        constraints=[],
        assumptions=[],
        opportunities=[],
        open_questions=[],
        summary=ResearchSummary(synthesis="B", key_takeaways=[]),
        confidence=1.0,
    )
```

Fixtures for shared setup:
```python
@pytest.fixture
def mock_settings() -> Settings:
    """Provide a clean settings instance for testing.
    
    This ensures that tests do not mutate or rely on global state.
    
    Returns:
        Settings: A mock-configured Settings object.
    """
    return Settings(
        environment=Environment.TESTING,
        debug=True,
        workspace_root=Path("/tmp/atlas_test_workspace"),
        log_level="DEBUG",
    )

@pytest.fixture
def repo() -> FakeMemoryRepository:
    return FakeMemoryRepository()
```

**Location:**
- `tests/conftest.py`: Global fixtures used across all tests
- Module-specific fixtures in test file itself
- Helper factories (functions, classes) defined in test file above test functions
- Integration test platform in `tests/support/test_bootstrap.py`

## Coverage

**Requirements:** No enforced minimum in config

**View Coverage:**
```bash
pytest --cov=engine --cov=interfaces --cov=shared --cov=clients --cov-report=term-missing --cov-report=xml
# Review in terminal:
# Name                                      Stmts   Miss  Cover   Missing
# -----------------------------------------------------------------------
# engine/research/services.py                 120     5    95%     45-47
```

Generated XML report: `coverage.xml` (for CI/CD integration)

## Test Types

**Unit Tests:**
- Location: `tests/[subsystem]/test_services.py`
- Scope: Test individual service methods
- Dependencies: Injected via constructor or fixtures
- Speed: Fast (milliseconds)
- Coverage: Business logic, validation, exception handling
- Example: `test_initialization_service()` tests `ResearchInitializationService.initialize_research()`

**Integration Tests:**
- Location: `tests/support/test_bootstrap.py` and multi-service tests
- Scope: Full workflow across multiple services
- Dependencies: Real filesystem repositories, mocked AI providers
- Setup: `create_test_platform(tmp_path)` assembles full dependency graph
- Example: Test that creates project → initializes research → adds evidence → creates planning

**E2E Tests:**
- Not explicitly present
- Closest equivalent: CLI tests in `tests/test_clients/cli/test_application.py`
- Mock the Atlas platform, test CLI argument parsing and output

## Common Patterns

**Async Testing:**
- Not used (project is synchronous)

**Error Testing:**
```python
def test_initialization_service(
    setup: tuple[FilesystemResearchRepository, UUID],
) -> None:
    repo, project_id = setup
    svc = ResearchInitializationService(repo)
    
    # First call succeeds
    svc.initialize_research(project_id, "Problem", ["Obj 1"])
    
    # Second call raises exception
    with pytest.raises(InvalidResearchOperationException):
        svc.initialize_research(project_id, "Another", [])
```

**Exception Message Validation:**
```python
def test_research_exceptions_instantiation() -> None:
    exc = ResearchNotFoundException("Not found")
    assert str(exc) == "Not found"
```

**Capturing Output:**
```python
def test_cli_app_run_ok(capsys: pytest.CaptureFixture[str]) -> None:
    app = CLIApplication(atlas_platform=MagicMock())
    app.run(["version"])
    
    out, err = capsys.readouterr()
    assert "ATLAS" in out
```

**Suppressing Linting Rules in Tests:**
```python
# Suppress "Magic number used" warning for confidence=0.95
assert snapshot.confidence == 0.95  # noqa: PLR2004
```

## Test Best Practices

1. **Descriptive Names**: Test name should describe what's being verified
   - Good: `test_initialization_service()`
   - Bad: `test_init()`

2. **One Assertion per Test** (guideline, not strict rule):
   - Multiple related assertions OK: all testing same behavior
   - Separate unrelated concerns into different tests

3. **Arrange-Act-Assert**:
   - Arrange: Set up test data and fixtures
   - Act: Call the function/method
   - Assert: Verify the result

4. **No Side Effects Between Tests**:
   - Fixtures use `tmp_path` for filesystem isolation
   - Mock objects reset between tests
   - Settings fixture creates fresh instance

5. **Fixture Naming**:
   - `setup`: Complex multi-value fixture for related objects
   - `repo`: Simple repository fixture
   - `mock_*`: Mocked objects
   - Descriptive names for domain object factories

---

*Testing analysis: 2026-07-19*
