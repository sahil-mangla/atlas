"""Rendering contract and base utilities for ATLAS client adapters.

Responsibilities
----------------
- Define the ``Renderable`` protocol all adapters implement
- Provide a ``RenderContext`` value object carrying adapter preferences
- Provide shared output helpers (heading, section, divider)

Adapters never share rendering state. Each adapter owns its renderer.
"""

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Render context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RenderContext:
    """Immutable rendering preferences for a specific adapter execution.

    Attributes:
        use_color: Whether ANSI color codes are supported.
        use_unicode: Whether Unicode box-drawing characters are supported.
        terminal_width: Maximum line width for the output medium.
        verbose: Whether verbose/debug output should be included.
    """

    use_color: bool = True
    use_unicode: bool = True
    terminal_width: int = 80
    verbose: bool = False


# ---------------------------------------------------------------------------
# Shared output helpers
# ---------------------------------------------------------------------------


def render_heading(
    title: str, *, level: int = 1, width: int = 80, use_unicode: bool = True
) -> str:
    """Render a section heading.

    Args:
        title: The heading text.
        level: Heading level (1 = major, 2 = sub).
        width: Terminal width used for level-1 underlines.
        use_unicode: Whether to use Unicode symbols.

    Returns:
        A formatted heading string.
    """
    if level == 1:
        char = "═" if use_unicode else "="
        underline = char * min(len(title), width)
        return f"{title}\n{underline}"

    prefix = "──" if use_unicode else "--"
    return f"{prefix} {title}"


def render_divider(
    *, char: str | None = None, width: int = 80, use_unicode: bool = True
) -> str:
    """Render a horizontal divider.

    Args:
        char: Character to repeat (defaults to ─ or - based on unicode).
        width: Total width of the divider.
        use_unicode: Whether to use Unicode symbols.

    Returns:
        A string of ``char`` repeated ``width`` times.
    """
    if char is None:
        char = "─" if use_unicode else "-"
    return char * width


def render_section(
    title: str, body: str, *, width: int = 80, use_unicode: bool = True
) -> str:
    """Render a labeled section with a sub-heading and body.

    Args:
        title: Section title.
        body: Section body text.
        width: Terminal width for the divider.
        use_unicode: Whether to use Unicode symbols.

    Returns:
        A formatted multi-line string.
    """
    heading = render_heading(title, level=2, width=width, use_unicode=use_unicode)
    return f"{heading}\n{body}"


def render_status_badge(label: str, *, ok: bool, use_unicode: bool = True) -> str:
    """Render a short status badge.

    Args:
        label: The status label text.
        ok: Whether the status is positive.
        use_unicode: Whether to use Unicode symbols.

    Returns:
        A string like ``[✓ ready]`` or ``[✗ failed]``.
    """
    icon = ("✓" if ok else "✗") if use_unicode else "v" if ok else "x"
    return f"[{icon} {label}]"
