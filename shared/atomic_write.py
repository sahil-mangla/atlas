"""Crash-safe file writes shared by all filesystem repositories."""

import os
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write ``content`` to ``path`` without ever leaving a truncated file.

    Writes to a temp file in the same directory (so the final ``os.replace``
    is on the same filesystem, keeping it atomic) then swaps it into place.
    A crash, kill, or full disk during the write leaves the original file
    untouched instead of corrupted.
    """
    directory = path.parent
    fd, tmp_name = tempfile.mkstemp(
        dir=directory, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        tmp_path.replace(path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
