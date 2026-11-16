"""Adapter capability declarations for the ATLAS client layer.

Responsibilities
----------------
- Define the ``AdapterCapabilities`` value object
- Declare the standard capability set for each implemented adapter
- Provide a helper to render a capability summary

Each adapter declares its capabilities at construction time. The platform
and shared utilities may use these declarations to adjust their output.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AdapterCapabilities:
    """Immutable declaration of what an adapter supports.

    Attributes:
        name: Human-readable adapter name (e.g. ``"CLI"``).
        supports_color: ANSI color codes are safe to emit.
        supports_progress: Progress animations are supported.
        supports_interactive: The adapter can prompt the user.
        supports_markdown: Rich markdown rendering is available.
        supports_unicode: Unicode characters render correctly.
    """

    name: str
    supports_color: bool = False
    supports_progress: bool = False
    supports_interactive: bool = False
    supports_markdown: bool = False
    supports_unicode: bool = False

    def render_summary(self) -> str:
        """Render a human-readable capability summary.

        Returns:
            A multi-line string listing capabilities and their status.
        """
        capabilities = {
            "Colors": self.supports_color,
            "Progress": self.supports_progress,
            "Interactive": self.supports_interactive,
            "Markdown": self.supports_markdown,
            "Unicode": self.supports_unicode,
        }
        lines = [self.name, ""]
        for cap, enabled in capabilities.items():
            tick = "✓" if enabled else "✗"
            lines.append(f"  {tick}  {cap}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Declared capability sets
# ---------------------------------------------------------------------------

#: Standard capabilities declared by the CLI adapter.
CLI_CAPABILITIES = AdapterCapabilities(
    name="CLI",
    supports_color=True,
    supports_progress=True,
    supports_interactive=True,
    supports_markdown=False,
    supports_unicode=True,
)
