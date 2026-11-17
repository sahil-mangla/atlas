"""Let users name projects instead of pasting UUIDs.

Every ``--project-id`` accepts a full UUID, a project name, its directory
slug, or a unique prefix of its ID (``atlas project list`` shows the first
eight characters). When the flag is left out, the current project is used:
the one last created or chosen with ``atlas project use``, or the only
active project if there is just one.
"""

import re
from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import UUID

from atlas_eng.results import ProjectResult
from atlas_eng.types import ProjectStatus

PROJECT_FLAG = "--project-id"
_STATE_FILE = ".atlas-current-project"
_MIN_PREFIX = 4
_HEX_PREFIX = re.compile(r"[0-9a-fA-F-]+")

ProjectLister = Callable[[], Sequence[ProjectResult]]


class ProjectReferenceError(Exception):
    """A project reference could not be resolved; the message says why."""


class CurrentProjectStore:
    """Remembers the current project in the workspace root.

    With no ``workspace`` (an injected platform, as in tests) the choice is
    kept in memory only, so nothing is written outside the test's control.
    """

    def __init__(self, workspace: Callable[[], Path] | None) -> None:
        self._workspace = workspace
        self._memory: UUID | None = None

    def _path(self) -> Path | None:
        return self._workspace() / _STATE_FILE if self._workspace else None

    def get(self) -> UUID | None:
        """The stored project ID, or ``None`` if unset or unreadable."""
        path = self._path()
        if path is None:
            return self._memory
        try:
            return UUID(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def set(self, project_id: UUID) -> None:
        """Make ``project_id`` the current project."""
        path = self._path()
        if path is None:
            self._memory = project_id
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{project_id}\n", encoding="utf-8")


def _slug(name: str) -> str:
    """Match the directory name the project repository derives from a name."""
    slug = re.sub(r"[^\w\s-]", "", name.lower().strip())
    return re.sub(r"[-\s]+", "-", slug)


def _describe(projects: Sequence[ProjectResult]) -> str:
    return ", ".join(f"'{p.name}' ({str(p.id)[:8]})" for p in projects)


def resolve_reference(value: str, projects: Sequence[ProjectResult]) -> UUID:
    """Turn a name, slug or ID prefix into a project ID.

    A full UUID is returned as given, even if unknown, so the platform
    reports a missing project the same way it always has.
    """
    text = value.strip()
    try:
        return UUID(text)
    except ValueError:
        pass
    folded = text.casefold()
    by_name = [
        p for p in projects if p.name.casefold() == folded or _slug(p.name) == folded
    ]
    if len(by_name) == 1:
        return by_name[0].id
    if len(by_name) > 1:
        raise ProjectReferenceError(
            f"More than one project is called {text!r}: {_describe(by_name)}. "
            "Use the ID prefix instead."
        )
    if len(text) >= _MIN_PREFIX and _HEX_PREFIX.fullmatch(text):
        by_prefix = [p for p in projects if str(p.id).startswith(text.lower())]
        if len(by_prefix) == 1:
            return by_prefix[0].id
        if len(by_prefix) > 1:
            raise ProjectReferenceError(
                f"ID prefix {text!r} matches several projects: "
                f"{_describe(by_prefix)}. Use more characters."
            )
    raise ProjectReferenceError(
        f"No project matches {text!r}. Run 'atlas project list' to see them."
    )


def default_project(current: UUID | None, projects: Sequence[ProjectResult]) -> UUID:
    """The project to use when ``--project-id`` is left out."""
    known = {p.id for p in projects}
    if current is not None and current in known:
        return current
    active = [p for p in projects if p.status != ProjectStatus.ARCHIVED]
    if len(active) == 1:
        return active[0].id
    if not active:
        raise ProjectReferenceError(
            "There are no projects yet. Create one with 'atlas project create' "
            "(or try 'atlas demo')."
        )
    raise ProjectReferenceError(
        "No current project, and there is more than one. Pass --project-id "
        "<name>, or choose a default with 'atlas project use --project-id <name>'."
    )


def resolve_given_reference(argv: list[str], projects: ProjectLister) -> list[str]:
    """Replace a non-UUID ``--project-id`` value in ``argv`` with the full UUID.

    The project list is only fetched when a value actually needs resolving.
    """
    for index, token in enumerate(argv):
        if token == PROJECT_FLAG and index + 1 < len(argv):
            value, rebuild = argv[index + 1], index + 1
        elif token.startswith(PROJECT_FLAG + "="):
            value, rebuild = token.partition("=")[2], index
        else:
            continue
        if _is_uuid(value):
            return argv
        resolved = str(resolve_reference(value, projects()))
        rewritten = list(argv)
        rewritten[rebuild] = (
            resolved if rebuild != index else f"{PROJECT_FLAG}={resolved}"
        )
        return rewritten
    return argv


def _is_uuid(value: str) -> bool:
    try:
        UUID(value.strip())
    except ValueError:
        return False
    return True
