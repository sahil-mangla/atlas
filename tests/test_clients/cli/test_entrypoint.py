"""Tests for the installed CLI entrypoint."""

import subprocess


def test_installed_cli_entrypoint() -> None:
    """Verify that the 'atlas' console script is installed and works."""
    # This invokes the entrypoint script created by the package manager
    result = subprocess.run(
        ["atlas", "help"], capture_output=True, text=True, check=False
    )

    # Check that it executed successfully
    assert result.returncode == 0
    # Check that the help output is correct
    assert "Usage:" in result.stdout
    assert "atlas <group> <sub-command>" in result.stdout
