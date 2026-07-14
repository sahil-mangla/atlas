"""CLI result renderer for the ATLAS client adapter.

Responsibilities
----------------
- Consume Result DTOs from the Atlas SDK
- Produce terminal-safe strings
- Delegate layout primitives to ``clients.common``

No Atlas SDK calls occur here. The renderer is a pure display layer:

    Result DTO → terminal string

All Result DTOs are imported from ``atlas.results``.
"""

from __future__ import annotations

import json
from typing import Any

from atlas.exceptions import ApplicationError
from atlas.results import (
    CommitResult,
    OperationResult,
    ProjectListResult,
    ProjectResult,
    ProposalResult,
    WorkflowStatusResult,
)
from clients.common.formatting import (
    render_key_value,
    render_list,
    render_markdown_block,
    render_table,
    truncate,
)
from clients.common.progress import ProgressTracker
from clients.common.rendering import (
    RenderContext,
    render_heading,
    render_section,
    render_status_badge,
)

# Default terminal width when none is provided
_DEFAULT_WIDTH = 80


class CLIRenderer:
    """Render Atlas Result DTOs to terminal-safe strings.

    Args:
        context: Rendering preferences for this session.
    """

    def __init__(self, context: RenderContext | None = None) -> None:
        self._ctx = context or RenderContext()

    # ------------------------------------------------------------------
    # Project results
    # ------------------------------------------------------------------

    def render_project(self, result: ProjectResult) -> str:
        """Render a single project summary.

        Args:
            result: The project result DTO.

        Returns:
            Formatted project card string.
        """
        heading = render_heading(result.name, width=self._ctx.terminal_width, use_unicode=self._ctx.use_unicode)  # noqa: E501
        pairs: dict[str, Any] = {
            "ID": str(result.id),
            "Status": result.status.value,
            "Description": truncate(result.description, 60),
            "Objective": truncate(result.objective, 60),
        }
        body = render_key_value(pairs)
        return f"{heading}\n{body}"

    def render_project_list(self, result: ProjectListResult) -> str:
        """Render a list of projects as a table.

        Args:
            result: The project list result DTO.

        Returns:
            Formatted table string.
        """
        if not result.projects:
            return "No projects found."
        heading = render_heading("Projects", width=self._ctx.terminal_width, use_unicode=self._ctx.use_unicode)  # noqa: E501
        rows = [
            [
                str(p.id)[:8] + "…",
                p.name,
                p.status.value,
                truncate(p.objective, 40),
            ]
            for p in result.projects
        ]
        table = render_table(
            ["ID", "Name", "Status", "Objective"],
            rows,
        )
        return f"{heading}\n\n{table}"

    # ------------------------------------------------------------------
    # Workflow results
    # ------------------------------------------------------------------

    def render_workflow_status(self, result: WorkflowStatusResult) -> str:
        """Render workflow status as a structured summary.

        Args:
            result: The workflow status result DTO.

        Returns:
            Formatted workflow status string.
        """
        heading = render_heading(
            "Workflow Status", width=self._ctx.terminal_width, use_unicode=self._ctx.use_unicode  # noqa: E501
        )
        ready_badge = render_status_badge(
            "ready" if result.is_ready_for_transition else "not ready",
            ok=result.is_ready_for_transition,
            use_unicode=self._ctx.use_unicode,
        )
        pairs: dict[str, Any] = {
            "Project": str(result.project_id),
            "Stage": result.current_stage.value,
            "Readiness": f"{result.readiness_status.value}  {ready_badge}",
        }
        summary = render_key_value(pairs)

        objectives_section = render_section(
            "Objectives",
            render_list(result.objectives),
            width=self._ctx.terminal_width,
            use_unicode=self._ctx.use_unicode,
        )

        parts = [heading, summary, objectives_section]
        if result.blocking_issues:
            issues_section = render_section(
                "Blocking Issues",
                render_list(result.blocking_issues),
                width=self._ctx.terminal_width,
                use_unicode=self._ctx.use_unicode,
            )
            parts.append(issues_section)

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Proposal results
    # ------------------------------------------------------------------

    def render_proposal(self, result: ProposalResult) -> str:
        """Render an AI proposal as a markdown-style summary.

        Args:
            result: The proposal result DTO.

        Returns:
            Formatted proposal string.
        """
        heading = render_heading("Proposal", width=self._ctx.terminal_width, use_unicode=self._ctx.use_unicode)  # noqa: E501
        pairs: dict[str, Any] = {
            "ID": str(result.id),
            "Project": str(result.project_id),
            "Stage": result.stage.value,
            "Status": result.status.value,
        }
        meta = render_key_value(pairs)

        content_str = _format_content(result.content)
        content_section = render_section(
            "Content",
            render_markdown_block(content_str, width=self._ctx.terminal_width),
            width=self._ctx.terminal_width,
            use_unicode=self._ctx.use_unicode,
        )
        return f"{heading}\n{meta}\n\n{content_section}"

    # ------------------------------------------------------------------
    # Operation / commit results
    # ------------------------------------------------------------------

    def render_operation(self, result: OperationResult) -> str:
        """Render a generic operation result.

        Args:
            result: The operation result DTO.

        Returns:
            A short status line.
        """
        badge = render_status_badge("ok" if result.success else "failed", ok=result.success, use_unicode=self._ctx.use_unicode)  # noqa: E501
        msg = f"  {result.message}" if result.message else ""
        return f"{badge}{msg}"

    def render_commit(self, result: CommitResult) -> str:
        """Render a proposal commit result.

        Args:
            result: The commit result DTO.

        Returns:
            A formatted commit summary.
        """
        badge = render_status_badge(
            "committed" if result.success else "failed", ok=result.success, use_unicode=self._ctx.use_unicode  # noqa: E501
        )
        pairs: dict[str, Any] = {
            "Proposal": str(result.proposal_id),
            "Summary": result.patch_summary,
        }
        return f"{badge}\n{render_key_value(pairs)}"

    # ------------------------------------------------------------------
    # Error rendering
    # ------------------------------------------------------------------

    def render_error(self, error: ApplicationError) -> str:
        """Render an AtlasError for terminal display.

        Args:
            error: The application error.

        Returns:
            A formatted error string.
        """
        badge = render_status_badge("error", ok=False, use_unicode=self._ctx.use_unicode)  # noqa: E501
        kind = type(error).__name__
        return f"{badge}  {kind}: {error}"

    def render_parse_error(self, message: str) -> str:
        """Render a parse error for terminal display.

        Args:
            message: The error message.

        Returns:
            A formatted error string.
        """
        badge = render_status_badge("parse error", ok=False, use_unicode=self._ctx.use_unicode)  # noqa: E501
        return f"{badge}  {message}"

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def render_progress_tracker(self, tracker: ProgressTracker) -> str:
        """Render the current state of a progress tracker.

        Args:
            tracker: The progress tracker to render.

        Returns:
            Multi-line progress summary.
        """
        return tracker.render(use_unicode=self._ctx.use_unicode)

    # ------------------------------------------------------------------
    # Information commands
    # ------------------------------------------------------------------

    def render_version(self, version: str) -> str:
        """Render the ATLAS version string.

        Args:
            version: The version string to display.

        Returns:
            A short version line.
        """
        return f"ATLAS  {version}"

    def render_help(self) -> str:
        """Render the CLI help text.

        Returns:
            Full CLI usage string.
        """
        return _HELP_TEXT


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_content(content: dict[str, Any]) -> str:
    """Format a content dictionary as a human-readable string.

    Args:
        content: The proposal content mapping.

    Returns:
        A JSON-formatted string.
    """
    try:
        return json.dumps(content, indent=2, default=str)
    except (TypeError, ValueError):
        return str(content)


_HELP_TEXT = """\
ATLAS Command Line Interface

Usage:
  atlas <group> <sub-command> [flags]

Project commands:
  atlas project create   --name <n> --description <d> --objective <o> [--path <p>]
  atlas project load     --project-id <uuid>
  atlas project list
  atlas project archive  --project-id <uuid>

Workflow commands:
  atlas workflow status      --project-id <uuid>
  atlas workflow transition  --project-id <uuid> [--reason <r>] [--actor <a>]

Stage commands:
  atlas stage execute  --project-id <uuid> --stage <stage>

Proposal commands:
  atlas proposal approve  --project-id <uuid> --proposal-id <uuid> [--actor <a>]
  atlas proposal reject   --project-id <uuid> --proposal-id <uuid> --feedback <f> [--actor <a>]

Information:
  atlas version
  atlas help

Valid stages:
  idea, research, problem_definition, planning, architecture,
  implementation, review, iteration, completion
"""  # noqa: E501
