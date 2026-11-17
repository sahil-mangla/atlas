"""Project references: names, slugs, ID prefixes and the current project."""

from pathlib import Path
from uuid import UUID

import pytest

from atlas_eng.clients.cli.project_reference import (
    CurrentProjectStore,
    ProjectReferenceError,
    default_project,
    resolve_given_reference,
    resolve_reference,
)
from atlas_eng.results import ProjectResult
from atlas_eng.types import ProjectStatus

ALPHA = UUID("aaaa1111-0000-4000-8000-000000000001")
ALPHA_TWIN = UUID("aaaa2222-0000-4000-8000-000000000002")
BETA = UUID("bbbb1111-0000-4000-8000-000000000003")


def _project(
    project_id: UUID, name: str, status: ProjectStatus = ProjectStatus.ACTIVE
) -> ProjectResult:
    return ProjectResult(
        id=project_id, name=name, description="d", objective="o", status=status
    )


PROJECTS = [
    _project(ALPHA, "Rollback Tool"),
    _project(ALPHA_TWIN, "Alpha Twin"),
    _project(BETA, "Beta", ProjectStatus.ARCHIVED),
]


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        (str(ALPHA), ALPHA),
        ("Rollback Tool", ALPHA),
        ("rollback tool", ALPHA),
        ("rollback-tool", ALPHA),
        ("aaaa1", ALPHA),
        ("AAAA2", ALPHA_TWIN),
        ("bbbb", BETA),
    ],
)
def test_references_resolve(reference: str, expected: UUID) -> None:
    assert resolve_reference(reference, PROJECTS) == expected


def test_unknown_full_uuid_passes_through_for_the_platform_to_reject() -> None:
    unknown = "00000000-0000-4000-8000-000000000000"

    assert str(resolve_reference(unknown, PROJECTS)) == unknown


@pytest.mark.parametrize(
    ("reference", "message"),
    [
        ("aaaa", "matches several projects"),
        ("abc", "No project matches"),  # too short to be a prefix
        ("nope", "No project matches"),
    ],
)
def test_unresolvable_references_explain_why(reference: str, message: str) -> None:
    with pytest.raises(ProjectReferenceError, match=message):
        resolve_reference(reference, PROJECTS)


def test_duplicate_names_are_ambiguous() -> None:
    twins = [_project(ALPHA, "Same"), _project(BETA, "Same")]

    with pytest.raises(ProjectReferenceError, match="More than one project"):
        resolve_reference("same", twins)


def test_default_prefers_the_current_project() -> None:
    assert default_project(ALPHA_TWIN, PROJECTS) == ALPHA_TWIN


def test_default_ignores_a_current_project_that_no_longer_exists() -> None:
    only = [_project(ALPHA, "Only")]

    assert default_project(BETA, only) == ALPHA


def test_default_uses_the_only_active_project() -> None:
    projects = [_project(ALPHA, "A"), _project(BETA, "B", ProjectStatus.ARCHIVED)]

    assert default_project(None, projects) == ALPHA


def test_default_refuses_to_guess_between_projects() -> None:
    with pytest.raises(ProjectReferenceError, match="project use"):
        default_project(None, PROJECTS)


def test_default_with_no_projects_suggests_creating_one() -> None:
    with pytest.raises(ProjectReferenceError, match="project create"):
        default_project(None, [])


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (
            ["workflow", "status", "--project-id", "rollback tool"],
            ["workflow", "status", "--project-id", str(ALPHA)],
        ),
        (
            ["workflow", "status", "--project-id=aaaa1"],
            ["workflow", "status", f"--project-id={ALPHA}"],
        ),
    ],
)
def test_argv_values_are_rewritten(argv: list[str], expected: list[str]) -> None:
    assert resolve_given_reference(argv, lambda: PROJECTS) == expected


def test_argv_with_a_uuid_or_no_flag_never_lists_projects() -> None:
    def fail() -> list[ProjectResult]:
        raise AssertionError("project list should not be needed")

    with_uuid = ["workflow", "status", "--project-id", str(ALPHA)]
    assert resolve_given_reference(with_uuid, fail) == with_uuid
    assert resolve_given_reference(["project", "list"], fail) == ["project", "list"]


def test_store_round_trips_through_the_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    store = CurrentProjectStore(lambda: workspace)

    assert store.get() is None
    store.set(ALPHA)

    assert CurrentProjectStore(lambda: workspace).get() == ALPHA


def test_store_ignores_a_corrupt_file(tmp_path: Path) -> None:
    (tmp_path / ".atlas-current-project").write_text("garbage", encoding="utf-8")

    assert CurrentProjectStore(lambda: tmp_path).get() is None


def test_store_without_a_workspace_stays_in_memory() -> None:
    store = CurrentProjectStore(None)
    store.set(BETA)

    assert store.get() == BETA
