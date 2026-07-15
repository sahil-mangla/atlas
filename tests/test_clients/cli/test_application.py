"""Tests for the CLI application."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from atlas.exceptions import ProjectNotFoundError
from atlas.results import ProjectResult
from atlas.types import ProjectStatus
from clients.cli.application import (
    _EXIT_ERROR,
    _EXIT_OK,
    _EXIT_PARSE_ERROR,
    CLIApplication,
    main,
)


def test_cli_app_run_ok(capsys: pytest.CaptureFixture[str]) -> None:
    mock_atlas = MagicMock()
    mock_atlas.create_project.return_value = ProjectResult(
        id=uuid.uuid4(),
        name="Test",
        description="Desc",
        objective="Obj",
        status=ProjectStatus.INITIALIZED,
    )
    app = CLIApplication(atlas_platform=mock_atlas)

    code = app.run(
        [
            "project",
            "create",
            "--name",
            "Test",
            "--description",
            "Desc",
            "--objective",
            "Obj",
        ]
    )

    assert code == _EXIT_OK
    mock_atlas.create_project.assert_called_once()
    out, _ = capsys.readouterr()
    assert "Test" in out


def test_cli_app_run_parse_error(capsys: pytest.CaptureFixture[str]) -> None:
    app = CLIApplication(atlas_platform=MagicMock())
    code = app.run(["project", "create", "--name", "Test"])  # missing flags
    assert code == _EXIT_PARSE_ERROR
    out, _ = capsys.readouterr()
    assert "parse error" in out
    assert "Missing required flags" in out


def test_cli_app_run_application_error(capsys: pytest.CaptureFixture[str]) -> None:
    mock_atlas = MagicMock()
    mock_atlas.load_project.side_effect = ProjectNotFoundError("Not found")
    app = CLIApplication(atlas_platform=mock_atlas)

    pid = str(uuid.uuid4())
    code = app.run(["project", "load", "--project-id", pid])

    assert code == _EXIT_ERROR
    out, _ = capsys.readouterr()
    assert "error" in out
    assert "ProjectNotFoundError" in out


def test_cli_app_version(capsys: pytest.CaptureFixture[str]) -> None:
    app = CLIApplication(atlas_platform=MagicMock())
    code = app.run(["version"])
    assert code == _EXIT_OK
    out, _ = capsys.readouterr()
    assert "ATLAS" in out


def test_cli_app_help(capsys: pytest.CaptureFixture[str]) -> None:
    app = CLIApplication(atlas_platform=MagicMock())
    code = app.run(["help"])
    assert code == _EXIT_OK
    out, _ = capsys.readouterr()
    assert "Usage:" in out


def test_cli_app_bootstrap_failure(capsys: pytest.CaptureFixture[str]) -> None:
    from atlas.exceptions import BootstrapError  # noqa: PLC0415

    with patch(
        "clients.cli.application.atlas.create",
        side_effect=BootstrapError("Failed to init"),
    ):  # noqa: E501, SIM117
        with patch("sys.exit") as mock_exit:
            main(["version"])
            mock_exit.assert_called_once_with(_EXIT_ERROR)
            _, err = capsys.readouterr()
            assert "BootstrapError" in err
            assert "Failed to init" in err


@patch("sys.exit")
def test_main(mock_exit: MagicMock) -> None:
    # Use patch to avoid actually hitting atlas.create() or sys.exit
    with patch(
        "clients.cli.application.CLIApplication.run", return_value=_EXIT_OK
    ) as mock_run:  # noqa: E501, SIM117
        with patch("clients.cli.application.atlas.create", return_value=MagicMock()):
            main(["version"])
            mock_run.assert_called_once_with(["version"])
            mock_exit.assert_called_once_with(_EXIT_OK)
