"""CLI command parser for the ATLAS client adapter.

Responsibilities
----------------
- Map ``sys.argv``-style token sequences to typed Command DTOs
- Validate argument presence and types at the transport boundary
- Raise ``CLIParseError`` on malformed input

No Atlas SDK calls occur here. The parser is a pure translation layer:

    argv → Command DTO

All Command DTOs are imported from ``atlas.commands``.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

from atlas.commands import (
    ApproveProposalCommand,
    ArchiveProjectCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    GetWorkflowStatusCommand,
    ListProjectsCommand,
    LoadProjectCommand,
    RejectProposalCommand,
    TransitionStageCommand,
)
from atlas.types import WorkflowStage

if TYPE_CHECKING:
    from atlas.commands import Command


class CLIParseError(ValueError):
    """Raised when argv cannot be translated to a valid Command DTO."""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class CommandParser:
    """Translate a flat argv token list into a typed Atlas Command DTO.

    Usage::

        parser = CommandParser()
        command = parser.parse(["project", "create",
                                "--name", "MyProj",
                                "--description", "...",
                                "--objective", "..."])

    Raises:
        CLIParseError: On missing arguments or unknown sub-commands.
    """

    def parse(self, argv: list[str]) -> Command:
        """Parse an argv token list.

        Args:
            argv: Tokens from the command line, **excluding** the program
                name (i.e. ``sys.argv[1:]``).

        Returns:
            The matching Command DTO.

        Raises:
            CLIParseError: When tokens cannot be resolved.
        """
        if not argv:
            raise CLIParseError("No command given. Run 'atlas help' for usage.")

        group = argv[0]
        dispatch: dict[str, Callable[[list[str]], Command]] = {
            "project": self._parse_project,
            "workflow": self._parse_workflow,
            "stage": self._parse_stage,
            "proposal": self._parse_proposal,
            "version": self._parse_version,
            "help": self._parse_help,
        }

        handler = dispatch.get(group)
        if handler is None:
            raise CLIParseError(
                f"Unknown command group '{group}'. Run 'atlas help' for usage."
            )
        return handler(argv[1:])

    # ------------------------------------------------------------------
    # Group parsers
    # ------------------------------------------------------------------

    def _parse_project(self, rest: list[str]) -> Command:
        if not rest:
            raise CLIParseError(
                "Missing project sub-command. "
                "Valid sub-commands: create, load, list, archive."
            )
        sub = rest[0]
        args = rest[1:]

        if sub == "create":
            return self._project_create(args)
        if sub == "load":
            return self._project_load(args)
        if sub == "list":
            return ListProjectsCommand()
        if sub == "archive":
            return self._project_archive(args)
        raise CLIParseError(
            f"Unknown project sub-command '{sub}'. Valid: create, load, list, archive."
        )

    def _parse_workflow(self, rest: list[str]) -> Command:
        if not rest:
            raise CLIParseError(
                "Missing workflow sub-command. Valid sub-commands: status, transition."
            )
        sub = rest[0]
        args = rest[1:]

        if sub == "status":
            return self._workflow_status(args)
        if sub == "transition":
            return self._workflow_transition(args)
        raise CLIParseError(
            f"Unknown workflow sub-command '{sub}'. Valid: status, transition."
        )

    def _parse_stage(self, rest: list[str]) -> Command:
        if not rest:
            raise CLIParseError(
                "Missing stage sub-command. Valid sub-commands: execute."
            )
        sub = rest[0]
        args = rest[1:]

        if sub == "execute":
            return self._stage_execute(args)
        raise CLIParseError(f"Unknown stage sub-command '{sub}'. Valid: execute.")

    def _parse_proposal(self, rest: list[str]) -> Command:
        if not rest:
            raise CLIParseError(
                "Missing proposal sub-command. Valid sub-commands: approve, reject."
            )
        sub = rest[0]
        args = rest[1:]

        if sub == "approve":
            return self._proposal_approve(args)
        if sub == "reject":
            return self._proposal_reject(args)
        raise CLIParseError(
            f"Unknown proposal sub-command '{sub}'. Valid: approve, reject."
        )

    def _parse_version(self, _rest: list[str]) -> Command:
        # Sentinel command — CLIApplication handles display directly.
        from clients.cli.commands import VersionCommand  # noqa: PLC0415

        return VersionCommand()

    def _parse_help(self, _rest: list[str]) -> Command:
        from clients.cli.commands import HelpCommand  # noqa: PLC0415

        return HelpCommand()

    # ------------------------------------------------------------------
    # Leaf builders
    # ------------------------------------------------------------------

    @staticmethod
    def _project_create(args: list[str]) -> CreateProjectCommand:
        parsed = _parse_flags(
            args,
            required=["--name", "--description", "--objective"],
            optional=["--path"],
        )
        return CreateProjectCommand(
            name=parsed["--name"],
            description=parsed["--description"],
            objective=parsed["--objective"],
            path=parsed.get("--path"),
        )

    @staticmethod
    def _project_load(args: list[str]) -> LoadProjectCommand:
        parsed = _parse_flags(args, required=["--project-id"])
        return LoadProjectCommand(project_id=_uuid(parsed["--project-id"]))

    @staticmethod
    def _project_archive(args: list[str]) -> ArchiveProjectCommand:
        parsed = _parse_flags(args, required=["--project-id"])
        return ArchiveProjectCommand(project_id=_uuid(parsed["--project-id"]))

    @staticmethod
    def _workflow_status(args: list[str]) -> GetWorkflowStatusCommand:
        parsed = _parse_flags(args, required=["--project-id"])
        return GetWorkflowStatusCommand(project_id=_uuid(parsed["--project-id"]))

    @staticmethod
    def _workflow_transition(args: list[str]) -> TransitionStageCommand:
        parsed = _parse_flags(
            args, required=["--project-id"], optional=["--reason", "--actor"]
        )
        return TransitionStageCommand(
            project_id=_uuid(parsed["--project-id"]),
            reason=parsed.get("--reason"),
            actor=parsed.get("--actor", "cli"),
        )

    @staticmethod
    def _stage_execute(args: list[str]) -> ExecuteStageCommand:
        parsed = _parse_flags(args, required=["--project-id", "--stage"])
        stage_val = parsed["--stage"]
        try:
            stage = WorkflowStage(stage_val)
        except ValueError:
            valid = ", ".join(s.value for s in WorkflowStage)
            raise CLIParseError(  # noqa: B904
                f"Invalid stage '{stage_val}'. Valid stages: {valid}."
            )
        return ExecuteStageCommand(
            project_id=_uuid(parsed["--project-id"]),
            stage=stage,
        )

    @staticmethod
    def _proposal_approve(args: list[str]) -> ApproveProposalCommand:
        parsed = _parse_flags(
            args,
            required=["--project-id", "--proposal-id"],
            optional=["--actor"],
        )
        return ApproveProposalCommand(
            project_id=_uuid(parsed["--project-id"]),
            proposal_id=_uuid(parsed["--proposal-id"]),
            actor=parsed.get("--actor", "cli"),
        )

    @staticmethod
    def _proposal_reject(args: list[str]) -> RejectProposalCommand:
        parsed = _parse_flags(
            args,
            required=["--project-id", "--proposal-id", "--feedback"],
            optional=["--actor"],
        )
        return RejectProposalCommand(
            project_id=_uuid(parsed["--project-id"]),
            proposal_id=_uuid(parsed["--proposal-id"]),
            feedback=parsed["--feedback"],
            actor=parsed.get("--actor", "cli"),
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_flags(
    tokens: list[str],
    *,
    required: list[str] | None = None,
    optional: list[str] | None = None,
) -> dict[str, str]:
    """Parse ``--flag value`` pairs from a flat token list.

    Args:
        tokens: Remaining argv tokens after the sub-command.
        required: Flags that must be present.
        optional: Flags that may be present.

    Returns:
        Mapping of flag name → value string.

    Raises:
        CLIParseError: On missing required flags or unknown flags.
    """
    required = required or []
    optional = optional or []
    known = set(required) | set(optional)

    result: dict[str, str] = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not token.startswith("--"):
            raise CLIParseError(f"Unexpected token '{token}'.")
        if token not in known:
            raise CLIParseError(f"Unknown flag '{token}'.")
        if i + 1 >= len(tokens):
            raise CLIParseError(f"Flag '{token}' requires a value.")
        result[token] = tokens[i + 1]
        i += 2

    missing = [f for f in required if f not in result]
    if missing:
        raise CLIParseError(f"Missing required flags: {', '.join(missing)}.")
    return result


def _uuid(raw: str) -> UUID:
    """Parse a UUID string, raising CLIParseError on failure.

    Args:
        raw: The raw UUID string from argv.

    Returns:
        Parsed UUID.

    Raises:
        CLIParseError: If the string is not a valid UUID.
    """
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise CLIParseError(f"'{raw}' is not a valid UUID.") from None


def build_parser() -> CommandParser:
    """Construct and return a ready-to-use ``CommandParser``.

    Returns:
        A configured ``CommandParser`` instance.
    """
    return CommandParser()


def parse_argv(argv: list[str] | None = None) -> Command:
    """Parse the process argv and return a Command DTO.

    Args:
        argv: Token list. Defaults to ``sys.argv[1:]``.

    Returns:
        The resolved Command DTO.

    Raises:
        CLIParseError: On parse failure.
    """
    if argv is None:
        argv = sys.argv[1:]
    return build_parser().parse(argv)
