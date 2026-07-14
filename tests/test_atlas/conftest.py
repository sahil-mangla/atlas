"""Fixtures for public Atlas SDK tests."""

from pathlib import Path

import pytest

from atlas import Atlas
from tests.support.test_bootstrap import create_test_platform


@pytest.fixture
def test_atlas_platform(tmp_path: Path) -> Atlas:
    return create_test_platform(tmp_path)
