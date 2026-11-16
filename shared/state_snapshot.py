"""Whole-directory rollback for operations that write several files.

A single file write is already atomic (see ``shared.atomic_write``), but an
operation such as approving a proposal updates several files in sequence. If
one of those writes fails, the earlier ones must be undone or the project is
left in a state no command can recover from. This captures the text state
files under a set of directories and can put them back exactly.
"""

from collections.abc import Iterable
from pathlib import Path

from shared.atomic_write import atomic_write_text

# Only ATLAS's own text records are captured. Binary caches (the sqlite
# vector index) are rebuildable and are deliberately left alone.
_STATE_SUFFIXES = frozenset({".json", ".md"})


class DirectoryStateSnapshot:
    """The contents of every state file under ``roots`` at capture time."""

    def __init__(self, roots: Iterable[Path]) -> None:
        self._roots = tuple(roots)
        self._files = {path: path.read_text(encoding="utf-8") for path in self._scan()}

    def _scan(self) -> list[Path]:
        return [
            path
            for root in self._roots
            if root.is_dir()
            for path in root.rglob("*")
            if path.is_file() and path.suffix in _STATE_SUFFIXES
        ]

    def restore(self) -> None:
        """Return every state file to its captured content.

        Files created since the capture are removed, changed files are
        rewritten and deleted files are recreated. Raises ``OSError`` if the
        filesystem still refuses writes, in which case the rollback is
        incomplete.
        """
        for path in self._scan():
            if path not in self._files:
                path.unlink(missing_ok=True)
        for path, content in self._files.items():
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                path.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_text(path, content)
