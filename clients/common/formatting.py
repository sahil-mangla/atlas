"""Text formatting utilities for ATLAS client adapters.

Responsibilities
----------------
- Tabular data rendering
- Ordered and unordered list rendering
- Markdown block rendering
- Tree structure rendering
- Text wrapping and truncation

No engineering transformations occur here. All inputs are plain Python
primitives or Result DTOs already projected from the Atlas SDK.
"""

import textwrap
from collections.abc import Sequence
from typing import Any

# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    min_col_width: int = 4,
) -> str:
    """Render a plain-text table with padded columns.

    Args:
        headers: Column header labels.
        rows: Sequence of row sequences; each row must have the same
            length as ``headers``.
        min_col_width: Minimum width for every column.

    Returns:
        A multi-line string representing the formatted table.
    """
    if not headers:
        return ""

    all_rows: list[Sequence[Any]] = [headers, *rows]
    col_widths = [
        max(min_col_width, *(len(str(r[i])) for r in all_rows))
        for i in range(len(headers))
    ]

    def _fmt_row(row: Sequence[Any]) -> str:
        cells = (str(row[i]).ljust(col_widths[i]) for i in range(len(headers)))
        return "  ".join(cells)

    separator = "  ".join("-" * w for w in col_widths)
    lines = [_fmt_row(headers), separator, *(_fmt_row(r) for r in rows)]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------


def render_list(items: Sequence[Any], *, bullet: str = "•") -> str:
    """Render an unordered list.

    Args:
        items: Items to render.
        bullet: The bullet character to use.

    Returns:
        A multi-line string with one item per line.
    """
    if not items:
        return "(none)"
    return "\n".join(f"{bullet} {item}" for item in items)


def render_ordered_list(items: Sequence[Any]) -> str:
    """Render a numbered list.

    Args:
        items: Items to render.

    Returns:
        A multi-line string with numbered items.
    """
    if not items:
        return "(none)"
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))


# ---------------------------------------------------------------------------
# Key-value pairs
# ---------------------------------------------------------------------------


def render_key_value(pairs: dict[str, Any], *, separator: str = ": ") -> str:
    """Render a dictionary as aligned key-value pairs.

    Args:
        pairs: Mapping of label → value.
        separator: String placed between key and value.

    Returns:
        A multi-line string with one pair per line.
    """
    if not pairs:
        return "(empty)"
    max_key = max(len(k) for k in pairs)
    return "\n".join(f"{k.ljust(max_key)}{separator}{v}" for k, v in pairs.items())


# ---------------------------------------------------------------------------
# Markdown block
# ---------------------------------------------------------------------------


def render_markdown_block(content: str, *, width: int = 80) -> str:
    """Wrap and clean a markdown content block for terminal display.

    Args:
        content: Raw markdown text.
        width: Target line width for wrapping.

    Returns:
        Wrapped text suitable for terminal output.
    """
    if not content:
        return ""
    lines = content.splitlines()
    wrapped = []
    for line in lines:
        if line.startswith(("#", "-", "*", ">", "```", "|")):
            wrapped.append(line)
        else:
            wrapped.append(textwrap.fill(line, width=width) if line else "")
    return "\n".join(wrapped)


# ---------------------------------------------------------------------------
# Tree
# ---------------------------------------------------------------------------


def render_tree(
    node: str,
    children: Sequence[Any],
    *,
    prefix: str = "",
    is_last: bool = True,
) -> str:
    """Render a hierarchical tree structure.

    Args:
        node: Label for this node.
        children: Child labels or nested ``(label, children)`` tuples.
        prefix: Internal prefix used during recursion.
        is_last: Whether this node is the last sibling.

    Returns:
        Multi-line string representing the tree.
    """
    connector = "└── " if is_last else "├── "
    lines = [f"{prefix}{connector}{node}"]
    child_prefix = prefix + ("    " if is_last else "│   ")
    for idx, child in enumerate(children):
        last_child = idx == len(children) - 1
        if isinstance(child, tuple) and len(child) == 2:  # noqa: PLR2004
            child_node, grandchildren = child
            lines.append(
                render_tree(
                    child_node,
                    grandchildren,
                    prefix=child_prefix,
                    is_last=last_child,
                )
            )
        else:
            conn = "└── " if last_child else "├── "
            lines.append(f"{child_prefix}{conn}{child}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------


def truncate(text: str, max_length: int, *, ellipsis: str = "…") -> str:
    """Truncate text to a maximum length with an ellipsis suffix.

    Args:
        text: Input text.
        max_length: Maximum number of characters.
        ellipsis: Suffix appended on truncation.

    Returns:
        Original text if within limit; truncated text otherwise.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(ellipsis)] + ellipsis
