"""Shared fixtures for testing the ATLAS foundation."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from atlas_eng.engine.config import Environment, Settings
from atlas_eng.shared.observability import tracing

_LANGFUSE_VARIABLES = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")


@pytest.fixture
def mock_settings() -> Settings:
    """Provide a clean settings instance for testing.

    This ensures that tests do not mutate or rely on global state.

    Returns:
        Settings: A mock-configured Settings object.
    """
    return Settings(
        environment=Environment.TESTING,
        workspace_root=Path("/tmp/atlas_test_workspace"),
    )


@pytest.fixture(autouse=True)
def _langfuse_off(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep Langfuse tracing off unless a test turns it on.

    Tracing reads the nearest ``.env``, and the suite runs from the repository
    root, where a developer's own ``.env`` may hold real Langfuse keys.
    """
    for name in _LANGFUSE_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(tracing, "_load_keys_from_dotenv", lambda: None)
    tracing.reset()
    yield
    tracing.reset()
    # Loading a .env exports values straight into os.environ, which
    # monkeypatch does not track; remove them before it restores originals.
    for name in _LANGFUSE_VARIABLES:
        os.environ.pop(name, None)
