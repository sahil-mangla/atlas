"""CLI Application — the entry point for the ATLAS CLI adapter.

Responsibilities
----------------
- Bootstrap the Atlas platform via ``atlas.create()``
- Dispatch the parsed Command DTO to the appropriate Atlas method
- Route Result DTOs through the renderer
- Catch only ``ApplicationError`` at the boundary
- Exit with the appropriate exit code

No engineering logic lives here. The application is a thin coordinator:

    Parser → Command DTO → Atlas → Result DTO → Renderer → stdout

Engine packages are never imported.
"""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import atlas
from atlas.adapters.protocol import (
    AdapterContext,
    AdapterKind,
    PlatformCapabilityManifest,
)
from atlas.capabilities.base import CapabilityName
from atlas.commands import (
    ApproveProposalCommand,
    ArchiveProjectCommand,
    CompleteObjectiveCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    GetWorkflowStatusCommand,
    ListKnowledgeCandidatesCommand,
    ListProjectsCommand,
    LoadProjectCommand,
    RejectProposalCommand,
    ReviewKnowledgeCandidateCommand,
    ShowKnowledgeCandidateCommand,
    TransitionStageCommand,
)
from atlas.contracts.version import PLATFORM_API_VERSION
from atlas.exceptions import ApplicationError
from clients.cli.commands import (
    HelpCommand,
    PresentationExportCommand,
    PresentationViewCommand,
    VersionCommand,
)
from clients.cli.parser import CLIParseError, parse_argv
from clients.cli.renderer import CLIRenderer
from clients.common.capabilities import CLI_CAPABILITIES
from clients.common.rendering import RenderContext

if TYPE_CHECKING:
    from atlas import Atlas
    from atlas.commands import Command

try:
    _VERSION = importlib.metadata.version("atlas")
except importlib.metadata.PackageNotFoundError:
    _VERSION = "0.0.0-dev"

# Exit codes
_EXIT_OK = 0
_EXIT_ERROR = 1
_EXIT_PARSE_ERROR = 2


class CLIApplication:
    """The ATLAS CLI application.

    Bootstraps Atlas, parses argv, dispatches commands, and renders
    output. This is the only class that calls ``atlas.create()``.

    Args:
        atlas_platform: An already-constructed Atlas facade, used
            primarily for testing. When ``None``, ``atlas.create()``
            is called at construction time.
        renderer: The renderer to use. Defaults to ``CLIRenderer()``.
    """

    def __init__(
        self,
        atlas_platform: Atlas | None = None,
        renderer: CLIRenderer | None = None,
    ) -> None:
        self._atlas = atlas_platform or atlas.create()
        self._renderer = renderer or CLIRenderer(
            RenderContext(
                use_unicode=_supports_unicode(),
                terminal_width=_terminal_width(),
            )
        )
        self._capabilities = CLI_CAPABILITIES
        self._adapter_context = AdapterContext(
            kind=AdapterKind.CLI, name="atlas-cli", version=_VERSION
        )

    @property
    def context(self) -> AdapterContext:
        """Return this adapter's identity for the platform's adapter boundary.

        Structurally satisfies ``atlas.adapters.protocol.PlatformAdapter``.
        """
        return self._adapter_context

    def negotiate(self, atlas_platform: Atlas) -> PlatformCapabilityManifest:  # noqa: ARG002
        """Return the capability manifest this adapter negotiates against.

        Static in Phase 15 -- all five platform capabilities are always
        present. The CLI continues to dispatch through named Atlas methods
        (see ``_dispatch`` below), not ``Atlas.handle()`` -- this method only
        proves structural conformance with ``PlatformAdapter``.
        """
        return PlatformCapabilityManifest(
            api_version=PLATFORM_API_VERSION,
            capabilities=(
                CapabilityName.PROJECT,
                CapabilityName.WORKFLOW,
                CapabilityName.WORKFLOW_EXECUTION,
                CapabilityName.KNOWLEDGE,
                CapabilityName.PRESENTATION,
            ),
        )

    def run(self, argv: list[str] | None = None) -> int:
        """Parse argv, execute the command, and write output to stdout.

        Args:
            argv: Token list. Defaults to ``sys.argv[1:]``.

        Returns:
            An integer exit code (0 = success, 1 = error, 2 = parse error).
        """
        try:
            command = parse_argv(argv)
        except CLIParseError as exc:
            sys.stdout.write(self._renderer.render_parse_error(str(exc)) + "\n")
            return _EXIT_PARSE_ERROR

        try:
            output = self._dispatch(command)
        except ApplicationError as exc:
            sys.stdout.write(self._renderer.render_error(exc) + "\n")
            return _EXIT_ERROR

        sys.stdout.write(output + "\n")
        return _EXIT_OK

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, command: Command) -> str:  # noqa: PLR0911, PLR0912
        """Route a command to the correct Atlas call.

        Args:
            command: The resolved command DTO.

        Returns:
            Rendered output string.

        Raises:
            ApplicationError: Propagated from the Atlas facade.
        """
        if isinstance(command, VersionCommand):
            return self._renderer.render_version(_VERSION)

        if isinstance(command, HelpCommand):
            return self._renderer.render_help()

        if isinstance(command, CreateProjectCommand):
            proj_res = self._atlas.create_project(command)
            return self._renderer.render_project(proj_res)

        if isinstance(command, LoadProjectCommand):
            load_res = self._atlas.load_project(command)
            return self._renderer.render_project(load_res)

        if isinstance(command, ListProjectsCommand):
            list_res = self._atlas.list_projects(command)
            return self._renderer.render_project_list(list_res)

        if isinstance(command, ArchiveProjectCommand):
            arch_res = self._atlas.archive_project(command)
            return self._renderer.render_operation(arch_res)

        if isinstance(command, GetWorkflowStatusCommand):
            stat_res = self._atlas.get_workflow_status(command)
            return self._renderer.render_workflow_status(stat_res)

        if isinstance(command, TransitionStageCommand):
            trans_res = self._atlas.transition_stage(command)
            return self._renderer.render_workflow_status(trans_res)

        if isinstance(command, CompleteObjectiveCommand):
            comp_res = self._atlas.complete_objective(command)
            return self._renderer.render_workflow_status(comp_res)

        if isinstance(command, ExecuteStageCommand):
            exec_res = self._atlas.execute_stage(command)
            return self._renderer.render_proposal(exec_res)

        if isinstance(command, ApproveProposalCommand):
            app_res = self._atlas.approve_proposal(command)
            return self._renderer.render_commit(app_res)

        if isinstance(command, RejectProposalCommand):
            rej_res = self._atlas.reject_proposal(command)
            return self._renderer.render_operation(rej_res)

        if isinstance(command, ListKnowledgeCandidatesCommand):
            list_kc_res = self._atlas.list_knowledge_candidates(command)
            return self._renderer.render_knowledge_candidate_list(list_kc_res)

        if isinstance(command, ShowKnowledgeCandidateCommand):
            show_kc_res = self._atlas.show_knowledge_candidate(command)
            return self._renderer.render_knowledge_candidate(show_kc_res)

        if isinstance(command, ReviewKnowledgeCandidateCommand):
            review_res = self._atlas.review_knowledge_candidate(command)
            return self._renderer.render_operation(review_res)

        if isinstance(command, PresentationViewCommand):
            view = self._get_view(command.view, command.project_id)
            rendered = self._atlas.render(view, command.format)
            return rendered.content.rstrip("\n")

        if isinstance(command, PresentationExportCommand):
            view = self._get_view(command.view, command.project_id)
            rendered = self._atlas.render(view, command.format)
            Path(command.output).write_text(rendered.content)
            return (
                f"Exported '{command.view}' view ({command.format}) "
                f"to {command.output}"
            )

        # Defensive: this path should never be reached with a valid Command.
        return f"Unhandled command type: {type(command).__name__}"

    def _get_view(self, view: str, project_id: UUID) -> Any:
        """Fetch the composed Phase 14 view named by a presentation command.

        Args:
            view: One of ``dashboard``, ``workflow``, ``research``,
                ``knowledge``, ``diagnostics`` -- already validated by the
                parser.
            project_id: The project to build the view for.

        Returns:
            The typed presentation view, ready to pass to ``Atlas.render``.
        """
        getters = {
            "dashboard": self._atlas.get_project_dashboard_view,
            "workflow": self._atlas.get_workflow_status_view,
            "research": self._atlas.get_research_summary_view,
            "knowledge": self._atlas.get_knowledge_summary_view,
            "diagnostics": self._atlas.get_diagnostics_view,
        }
        return getters[view](project_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _terminal_width() -> int:
    """Return the current terminal width, defaulting to 80.

    Returns:
        Number of columns in the terminal.
    """
    try:
        import shutil  # noqa: PLC0415

        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def _supports_unicode() -> bool:
    """Best-effort detection of whether stdout can safely render Unicode.

    Returns:
        True if stdout's encoding can represent a sample Unicode symbol.
    """
    encoding = getattr(sys.stdout, "encoding", None)
    if not encoding:
        return False
    try:
        "✓".encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point.

    Constructs a ``CLIApplication`` and exits with its return code.

    Args:
        argv: Optional argv override for testing.
    """
    from atlas.exceptions import ApplicationError  # noqa: PLC0415

    try:
        app = CLIApplication()
        code = app.run(argv)
    except ApplicationError as exc:
        # Fallback renderer for bootstrap failures before CLIApplication is alive
        sys.stderr.write(f"[✗ error]  {type(exc).__name__}: {exc}\n")
        code = _EXIT_ERROR

    sys.exit(code)
