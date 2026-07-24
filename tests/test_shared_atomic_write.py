"""Tests for the crash-safe atomic write helper."""

from pathlib import Path
from unittest.mock import patch

import pytest

from shared.atomic_write import atomic_write_text


def test_writes_content_to_target_path(tmp_path: Path) -> None:
    target = tmp_path / "data.json"

    atomic_write_text(target, '{"a": 1}')

    assert target.read_text(encoding="utf-8") == '{"a": 1}'


def test_overwrites_existing_content(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    target.write_text("old", encoding="utf-8")

    atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "new"


def test_leaves_original_file_untouched_when_replace_fails(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    target.write_text("original", encoding="utf-8")

    with (
        patch("shared.atomic_write.Path.replace", side_effect=OSError("disk full")),
        pytest.raises(OSError, match="disk full"),
    ):
        atomic_write_text(target, "corrupted-write")

    assert target.read_text(encoding="utf-8") == "original"


def test_does_not_leave_a_temp_file_behind_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "data.json"

    with (
        patch("shared.atomic_write.Path.replace", side_effect=OSError("disk full")),
        pytest.raises(OSError),
    ):
        atomic_write_text(target, "content")

    leftover = list(tmp_path.iterdir())
    assert leftover == []


def test_no_target_file_created_when_write_fails_before_replace(tmp_path: Path) -> None:
    target = tmp_path / "data.json"

    with (
        patch("shared.atomic_write.os.fsync", side_effect=OSError("io error")),
        pytest.raises(OSError, match="io error"),
    ):
        atomic_write_text(target, "content")

    assert not target.exists()
    assert list(tmp_path.iterdir()) == []
