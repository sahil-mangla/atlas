"""Tests for clients/common/formatting.py, focused on RC-007's ASCII
fallback guarantee -- every shared rendering primitive that defaults to a
Unicode symbol must offer an ASCII-safe path for non-Unicode terminals."""

from clients.common.formatting import render_list, render_tree, truncate


def test_render_list_default_bullet_is_unicode() -> None:
    assert render_list(["a", "b"]) == "• a\n• b"


def test_render_list_ascii_bullet_override() -> None:
    out = render_list(["a", "b"], bullet="-")
    assert "•" not in out
    assert out == "- a\n- b"


def test_render_tree_unicode_by_default() -> None:
    out = render_tree("root", ["child"])
    assert "└── " in out


def test_render_tree_ascii_fallback_has_no_box_drawing_characters() -> None:
    out = render_tree("root", ["child1", "child2"], use_unicode=False)
    assert "└" not in out
    assert "├" not in out
    assert "│" not in out
    assert "`-- child2" in out
    assert "|-- child1" in out


def test_render_tree_ascii_fallback_nested() -> None:
    out = render_tree("root", [("branch", ["leaf1", "leaf2"])], use_unicode=False)
    assert "└" not in out
    assert "├" not in out
    assert "│" not in out


def test_truncate_default_ellipsis_is_unicode() -> None:
    assert truncate("abcdefgh", 5).endswith("…")


def test_truncate_ascii_ellipsis_override() -> None:
    out = truncate("abcdefgh", 6, ellipsis="...")
    assert "…" not in out
    assert out.endswith("...")
