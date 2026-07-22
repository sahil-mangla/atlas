"""CLI-only command sentinel types.

The ATLAS public SDK does not model ``version`` or ``help`` because they
carry no platform intent. These are handled entirely within the CLI adapter
and never forwarded to Atlas.

``PresentationViewCommand`` / ``PresentationExportCommand`` are also CLI-only:
Phase 14's typed views (``Atlas.get_*_view``) and generic ``Atlas.render``
are a read-only query API deliberately kept outside the
Command/``Atlas._dispatch`` envelope (see
``docs/architecture/presentation-layer.md``), so these wrap that query shape
for the CLI's own dispatch rather than being added to ``atlas.commands``.
"""

from uuid import UUID

from atlas.commands import Command


class VersionCommand(Command):
    """CLI sentinel: display the current ATLAS version."""


class HelpCommand(Command):
    """CLI sentinel: display CLI usage information."""


class PresentationViewCommand(Command):
    """CLI sentinel: render one composed presentation view to stdout."""

    project_id: UUID
    view: str
    format: str = "cli"


class PresentationExportCommand(Command):
    """CLI sentinel: render one composed presentation view to a file."""

    project_id: UUID
    view: str
    format: str
    output: str
