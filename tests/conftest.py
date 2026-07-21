"""Shared fixtures for testing the ATLAS foundation."""

from pathlib import Path

import pytest

from engine.config import Environment, Settings


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
