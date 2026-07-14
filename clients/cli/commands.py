"""CLI-only command sentinel types.

The ATLAS public SDK does not model ``version`` or ``help`` because they
carry no platform intent. These are handled entirely within the CLI adapter
and never forwarded to Atlas.
"""

from atlas.commands import Command


class VersionCommand(Command):
    """CLI sentinel: display the current ATLAS version."""


class HelpCommand(Command):
    """CLI sentinel: display CLI usage information."""
