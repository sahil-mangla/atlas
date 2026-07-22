"""RC-003 regression: presentation views (dashboard, workflow, research,
knowledge, diagnostics) and export are reachable through the CLI.

Before this fix, ``Atlas.get_*_view`` and ``Atlas.render`` (the Phase 14
typed-view/rendering API) existed and were fully functional, but
``clients/cli`` had no ``presentation`` command group at all -- no parser
branch, no dispatch, no renderer output -- so a CLI user could never
generate a dashboard, export a diagnostics report, etc.
"""

import json
import uuid
from pathlib import Path

import pytest

from atlas import Atlas
from clients.cli.application import _EXIT_ERROR, _EXIT_OK, CLIApplication
from tests.support.test_bootstrap import create_test_platform


@pytest.fixture
def platform(tmp_path: Path) -> Atlas:
    return create_test_platform(tmp_path)


@pytest.fixture
def app(platform: Atlas) -> CLIApplication:
    return CLIApplication(atlas_platform=platform)


@pytest.fixture
def project_id(app: CLIApplication, capsys: pytest.CaptureFixture[str]) -> str:
    code = app.run(
        [
            "project",
            "create",
            "--name",
            "RC-003 Smoke",
            "--description",
            "D",
            "--objective",
            "O",
        ]
    )
    assert code == _EXIT_OK
    out, _ = capsys.readouterr()
    for line in out.splitlines():
        if line.startswith("ID"):
            return line.split(":", 1)[1].strip()
    raise AssertionError(f"Could not find project ID in output:\n{out}")


@pytest.mark.parametrize(
    "view", ["dashboard", "workflow", "research", "knowledge", "diagnostics"]
)
def test_presentation_view_cli_format(
    app: CLIApplication,
    project_id: str,
    capsys: pytest.CaptureFixture[str],
    view: str,
) -> None:
    code = app.run(["presentation", view, "--project-id", project_id])
    assert code == _EXIT_OK
    out, _ = capsys.readouterr()
    assert out.strip()
    # The 'cli' renderer strips markdown markers -- no literal ** or headers.
    assert "**" not in out


def test_presentation_view_json_format_is_valid_json(
    app: CLIApplication, project_id: str, capsys: pytest.CaptureFixture[str]
) -> None:
    code = app.run(
        ["presentation", "dashboard", "--project-id", project_id, "--format", "json"]
    )
    assert code == _EXIT_OK
    out, _ = capsys.readouterr()
    parsed = json.loads(out)
    assert parsed["kind"] == "project_dashboard"
    assert parsed["project_id"] == project_id


def test_presentation_view_markdown_format(
    app: CLIApplication, project_id: str, capsys: pytest.CaptureFixture[str]
) -> None:
    code = app.run(
        [
            "presentation",
            "diagnostics",
            "--project-id",
            project_id,
            "--format",
            "markdown",
        ]
    )
    assert code == _EXIT_OK
    out, _ = capsys.readouterr()
    assert out.startswith("# ")


def test_presentation_export_writes_file(
    app: CLIApplication,
    project_id: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "dashboard.json"
    code = app.run(
        [
            "presentation",
            "export",
            "--project-id",
            project_id,
            "--view",
            "dashboard",
            "--output",
            str(output_path),
            "--format",
            "json",
        ]
    )
    assert code == _EXIT_OK
    out, _ = capsys.readouterr()
    assert str(output_path) in out
    assert output_path.exists()
    written = json.loads(output_path.read_text())
    assert written["kind"] == "project_dashboard"


def test_presentation_view_nonexistent_project_is_application_error(
    app: CLIApplication, capsys: pytest.CaptureFixture[str]
) -> None:
    code = app.run(
        ["presentation", "dashboard", "--project-id", str(uuid.uuid4())]
    )
    assert code == _EXIT_ERROR
    out, _ = capsys.readouterr()
    assert "ProjectNotFoundError" in out
