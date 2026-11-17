"""CLI Application — the entry point for the ATLAS CLI adapter.

Responsibilities
----------------
- Bootstrap the Atlas platform via ``atlas_eng.create()``
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

import atlas_eng
from atlas_eng.adapters.protocol import (
    AdapterContext,
    AdapterKind,
    PlatformCapabilityManifest,
)
from atlas_eng.capabilities.base import CapabilityName
from atlas_eng.clients.cli.commands import (
    DemoCommand,
    DoctorCommand,
    HelpCommand,
    InitCommand,
    PresentationExportCommand,
    PresentationViewCommand,
    UseProjectCommand,
    VersionCommand,
)
from atlas_eng.clients.cli.onboarding import (
    OnboardingError,
    run_demo,
    run_doctor,
    run_init,
)
from atlas_eng.clients.cli.parser import CLIParseError, MissingFlagsError, parse_argv
from atlas_eng.clients.cli.project_reference import (
    PROJECT_FLAG,
    CurrentProjectStore,
    ProjectReferenceError,
    default_project,
    resolve_given_reference,
)
from atlas_eng.clients.cli.renderer import CLIRenderer
from atlas_eng.clients.common.capabilities import CLI_CAPABILITIES
from atlas_eng.clients.common.rendering import RenderContext
from atlas_eng.commands import (
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
from atlas_eng.contracts.version import PLATFORM_API_VERSION
from atlas_eng.exceptions import ApplicationError
from atlas_eng.results import ProjectResult
from atlas_eng.setup import workspace_root

if TYPE_CHECKING:
    from atlas_eng import Atlas
    from atlas_eng.commands import Command

try:
    _VERSION = importlib.metadata.version("atlas-eng")
except importlib.metadata.PackageNotFoundError:
    _VERSION = "0.0.0-dev"

# Exit codes
_EXIT_OK = 0
_EXIT_ERROR = 1
_EXIT_PARSE_ERROR = 2


class CLIApplication:
    """The ATLAS CLI application.

    Bootstraps Atlas, parses argv, dispatches commands, and renders
    output. This is the only class that calls ``atlas_eng.create()``.

    Args:
        atlas_platform: An already-constructed Atlas facade, used
            primarily for testing. When ``None``, ``atlas_eng.create()``
            is called at construction time.
        renderer: The renderer to use. Defaults to ``CLIRenderer()``.
    """

    def __init__(
        self,
        atlas_platform: Atlas | None = None,
        renderer: CLIRenderer | None = None,
    ) -> None:
        # Created on first use, not here: 'init', 'doctor', 'demo', 'help'
        # and 'version' must work while the configuration is missing or
        # broken, and should not pay the platform's start-up cost.
        self._atlas_platform = atlas_platform
        self._renderer = renderer or CLIRenderer(
            RenderContext(
                use_unicode=_supports_unicode(),
                terminal_width=_terminal_width(),
            )
        )
        self._capabilities = CLI_CAPABILITIES
        # Remembered on disk only for the real platform; an injected one (as
        # in tests) keeps the choice in memory.
        self._current_project = CurrentProjectStore(
            None if atlas_platform is not None else workspace_root
        )
        self._adapter_context = AdapterContext(
            kind=AdapterKind.CLI, name="atlas-cli", version=_VERSION
        )

    @property
    def _atlas(self) -> Atlas:
        if self._atlas_platform is None:
            self._atlas_platform = atlas_eng.create()
        return self._atlas_platform

    @property
    def context(self) -> AdapterContext:
        """Return this adapter's identity for the platform's adapter boundary.

        Structurally satisfies ``atlas_eng.adapters.protocol.PlatformAdapter``.
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
        tokens = list(sys.argv[1:] if argv is None else argv)
        try:
            command = self._parse(tokens)
        except (CLIParseError, ProjectReferenceError) as exc:
            sys.stdout.write(self._renderer.render_parse_error(str(exc)) + "\n")
            return _EXIT_PARSE_ERROR
        except ApplicationError as exc:
            sys.stdout.write(self._renderer.render_error(exc) + "\n")
            return _EXIT_ERROR

        code = _EXIT_OK
        try:
            if isinstance(command, InitCommand | DoctorCommand | DemoCommand):
                output, code = self._run_onboarding(command)
            else:
                output = self._dispatch(command)
        except ApplicationError as exc:
            sys.stdout.write(self._renderer.render_error(exc) + "\n")
            return _EXIT_ERROR
        except OnboardingError as exc:
            sys.stdout.write(self._renderer.render_failure(str(exc)) + "\n")
            return _EXIT_ERROR

        sys.stdout.write(output + "\n")
        return code

    def _parse(self, tokens: list[str]) -> Command:
        """Parse ``tokens``, resolving project names and the current project."""
        tokens = resolve_given_reference(tokens, self._list_projects)
        try:
            return parse_argv(tokens)
        except MissingFlagsError as exc:
            if PROJECT_FLAG not in exc.flags:
                raise
            project_id = default_project(
                self._current_project.get(), self._list_projects()
            )
            return parse_argv([*tokens, PROJECT_FLAG, str(project_id)])

    def _list_projects(self) -> list[ProjectResult]:
        return self._atlas.list_projects(ListProjectsCommand()).projects

    def _run_onboarding(
        self, command: InitCommand | DoctorCommand | DemoCommand
    ) -> tuple[str, int]:
        """Run a first-run command; these never use the configured platform."""
        if isinstance(command, InitCommand):
            return run_init(command, cwd=Path.cwd(), out=sys.stdout), _EXIT_OK
        if isinstance(command, DoctorCommand):
            report, ok = run_doctor(command, use_unicode=_supports_unicode())
            return report, _EXIT_OK if ok else _EXIT_ERROR
        return run_demo(command, out=sys.stdout), _EXIT_OK

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
            self._current_project.set(proj_res.id)
            return (
                self._renderer.render_project(proj_res)
                + "\n\nThis is now the current project: commands that take "
                "--project-id use it when the flag is left out."
            )

        if isinstance(command, UseProjectCommand):
            use_res = self._atlas.load_project(
                LoadProjectCommand(project_id=command.project_id)
            )
            self._current_project.set(use_res.id)
            return (
                f"Now using project '{use_res.name}' ({str(use_res.id)[:8]}). "
                "Commands that take --project-id use it when the flag is left out."
            )

        if isinstance(command, LoadProjectCommand):
            load_res = self._atlas.load_project(command)
            return self._renderer.render_project(load_res)

        if isinstance(command, ListProjectsCommand):
            list_res = self._atlas.list_projects(command)
            return self._renderer.render_project_list(
                list_res, current_id=self._current_project.get()
            )

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
            return self._renderer.render_knowledge_candidate_list(
                list_kc_res, output_format=command.format
            )

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
            try:
                Path(command.output).write_text(rendered.content, encoding="utf-8")
            except (OSError, UnicodeEncodeError) as exc:
                raise ApplicationError(
                    f"Failed to write export to '{command.output}': {exc}"
                ) from exc
            return (
                f"Exported '{command.view}' view ({command.format}) to {command.output}"
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
    from atlas_eng.exceptions import ApplicationError  # noqa: PLC0415

    try:
        app = CLIApplication()
        code = app.run(argv)
    except ApplicationError as exc:
        # Fallback renderer for bootstrap failures before CLIApplication is alive
        sys.stderr.write(f"[✗ error]  {type(exc).__name__}: {exc}\n")
        code = _EXIT_ERROR

    sys.exit(code)
