"""Progress rendering primitives for ATLAS client adapters.

Responsibilities
----------------
- Progress bar rendering (text-only, no ANSI requirements)
- Step-based progress tracking
- Spinner frame generation

The platform owns progress *generation*. This module owns display only.
Each adapter consumes these primitives and renders them in its own medium.
"""

from dataclasses import dataclass, field
from typing import ClassVar

# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------


def render_progress_bar(  # noqa: PLR0913
    current: int,
    total: int,
    *,
    width: int = 20,
    fill: str | None = None,
    empty: str | None = None,
    use_unicode: bool = True,
) -> str:
    """Render a text progress bar.

    Args:
        current: Current progress value.
        total: Maximum progress value.
        width: Number of bar characters.
        fill: Character for completed portion.
        empty: Character for remaining portion.

    Returns:
        A progress bar string like ``████████░░░░``.

    Example::

        render_progress_bar(4, 10, width=10)
        # '████░░░░░░'
    """
    if fill is None:
        fill = "█" if use_unicode else "#"
    if empty is None:
        empty = "░" if use_unicode else "-"

    filled = 0 if total <= 0 else min(width, round(current / total * width))
    bar = fill * filled + empty * (width - filled)
    pct = 0 if total <= 0 else min(100, round(current / total * 100))
    return f"{bar} {pct:>3}%"


# ---------------------------------------------------------------------------
# Step tracker
# ---------------------------------------------------------------------------


@dataclass
class ProgressTracker:
    """Tracks named steps and exposes a renderable summary.

    Attributes:
        steps: Ordered list of step labels.
        completed: Set of completed step labels.
        current: Currently active step label, or ``None``.
    """

    steps: list[str] = field(default_factory=list)
    completed: set[str] = field(default_factory=set)
    current: str | None = None

    def start(self, step: str) -> None:
        """Mark a step as the active step.

        Args:
            step: Step label to mark as current.
        """
        if step not in self.steps:
            self.steps.append(step)
        self.current = step

    def complete(self, step: str) -> None:
        """Mark a step as completed.

        Args:
            step: Step label to mark complete.
        """
        self.completed.add(step)
        if self.current == step:
            self.current = None

    def render(self, use_unicode: bool = True) -> str:
        """Render the current progress as a multi-line string.

        Args:
            use_unicode: Whether to use Unicode symbols.

        Returns:
            A formatted string listing all steps and their status.
        """
        lines = []
        for step in self.steps:
            if step in self.completed:
                indicator = "✓" if use_unicode else "v"
            elif step == self.current:
                indicator = "→" if use_unicode else ">"
            else:
                indicator = "○" if use_unicode else " "
            lines.append(f"  {indicator}  {step}")
        return "\n".join(lines) if lines else ""


# ---------------------------------------------------------------------------
# Spinner
# ---------------------------------------------------------------------------


class Spinner:
    """Provides spinner frames for animated terminal progress.

    This class generates frames only. Actual I/O is the adapter's concern.

    Attributes:
        FRAMES: The default unicode frame sequence.
        ASCII_FRAMES: Fallback ascii frame sequence.
    """

    FRAMES: ClassVar[list[str]] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    ASCII_FRAMES: ClassVar[list[str]] = ["|", "/", "-", "\\"]

    def __init__(self) -> None:
        self._index: int = 0

    def next_frame(self, use_unicode: bool = True) -> str:
        """Advance to the next spinner frame and return it.

        Args:
            use_unicode: Whether to use Unicode symbols.

        Returns:
            The current spinner character.
        """
        frames = self.FRAMES if use_unicode else self.ASCII_FRAMES
        frame = frames[self._index % len(frames)]
        self._index += 1
        return frame

    def reset(self) -> None:
        """Reset the spinner to its initial frame."""
        self._index = 0
