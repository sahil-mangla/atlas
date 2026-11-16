"""First-run commands: ``atlas init``, ``atlas doctor`` and ``atlas demo``.

None of these use the user's configured platform: ``init`` and ``doctor``
must work while the configuration is still missing or broken, and ``demo``
builds its own offline platform in a throwaway directory.
"""

import contextlib
import getpass
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

import atlas_eng
from atlas_eng.clients.cli.commands import DemoCommand, DoctorCommand, InitCommand
from atlas_eng.commands import (
    ApproveProposalCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    ListKnowledgeCandidatesCommand,
    TransitionStageCommand,
)
from atlas_eng.setup import (
    PROTOCOLS,
    CheckStatus,
    ConfigurationReport,
    ProtocolSetup,
    diagnose,
    extra_installed,
    make_demo_workspace,
    protocol_setup,
    render_env_file,
)
from atlas_eng.types import WorkflowStage

_STATUS_MARKS = {
    CheckStatus.OK: ("✓", "ok"),
    CheckStatus.WARN: ("!", "warn"),
    CheckStatus.FAIL: ("✗", "FAIL"),
}

# The one field of each stage's draft that sums it up in a line.
_HEADLINES = {
    WorkflowStage.RESEARCH: "problem_statement",
    WorkflowStage.PLANNING: "scope_statement",
    WorkflowStage.ARCHITECTURE: "design_summary",
    WorkflowStage.REVIEW: "synthesis",
}

Prompt = Callable[[str], str]


class OnboardingError(Exception):
    """A first-run command could not complete; the message says why.

    CLI-local on purpose: it never crosses the platform boundary, so it is
    not an ``ApplicationError`` with a platform error code.
    """


# ---------------------------------------------------------------------------
# atlas init
# ---------------------------------------------------------------------------


def run_init(
    command: InitCommand,
    *,
    cwd: Path,
    out: TextIO,
    ask: Prompt | None = None,
    ask_secret: Prompt | None = None,
) -> str:
    """Write ``.env`` in ``cwd`` for the chosen protocol.

    Prompts only for what the flags did not supply, and only when stdin is
    a terminal; otherwise unanswered values are left commented out in the
    file. API keys are only ever read through ``ask_secret`` (no echo), never
    from flags, so they do not end up in shell history.
    """
    interactive = ask is not None or sys.stdin.isatty()
    ask = ask or input
    ask_secret = ask_secret or getpass.getpass
    env_path = cwd / ".env"
    if env_path.exists() and not command.force:
        raise OnboardingError(
            f"{env_path} already exists. Edit it directly, or run "
            "'atlas init --force' to replace it (the old file is kept as "
            ".env.bak)."
        )

    setup = _choose_protocol(command.protocol, interactive, ask, out)
    flag_values = {
        "ATLAS_AI_MODEL": command.model,
        "ATLAS_GEMINI_MODEL": command.model,
        "ATLAS_AI_ENDPOINT": command.endpoint,
    }
    values: dict[str, str] = {}
    for variable in setup.variables:
        given = flag_values.get(variable.name)
        if given:
            values[variable.name] = given
            continue
        if not interactive:
            if variable.default:
                values[variable.name] = variable.default
            continue
        suffix = f" [{variable.default}]" if variable.default else ""
        reader = ask_secret if variable.secret else ask
        answer = reader(f"{variable.prompt}{suffix}: ").strip()
        if answer or variable.default:
            values[variable.name] = answer or variable.default

    if env_path.exists():
        shutil.copy2(env_path, cwd / ".env.bak")
    env_path.write_text(render_env_file(setup, values), encoding="utf-8")
    # Owner-only, as it may hold an API key. Not every filesystem supports
    # it; the file is still written.
    with contextlib.suppress(OSError):
        env_path.chmod(0o600)

    lines = [f"Wrote {env_path} for {setup.name}."]
    missing = [v.name for v in setup.variables if v.required and v.name not in values]
    if missing:
        lines.append(f"Still to fill in: {', '.join(missing)}.")
    if not extra_installed(setup):
        lines.append(f"{setup.name} also needs: pip install 'atlas-eng[{setup.extra}]'")
    if _tracked_by_git(env_path):
        lines.append(
            "Warning: .env is not ignored by git. Add .env and .env.bak to "
            ".gitignore so API keys are never committed."
        )
    lines.append("Next: run 'atlas doctor' to check the configuration.")
    return "\n".join(lines)


def _choose_protocol(
    requested: str | None, interactive: bool, ask: Prompt, out: TextIO
) -> ProtocolSetup:
    if requested:
        setup = protocol_setup(requested)
        if setup is None:
            known = ", ".join(p.name for p in PROTOCOLS)
            raise OnboardingError(
                f"Unknown protocol {requested!r}. Choose one of: {known}."
            )
        return setup
    if not interactive:
        raise OnboardingError(
            "No terminal to ask in. Pass the protocol: "
            "atlas init --protocol <GEMINI|ANTHROPIC|OPENAI_COMPATIBLE|OLLAMA|SCRIPTED>"
        )
    out.write("Which AI provider should ATLAS use?\n")
    for index, setup in enumerate(PROTOCOLS, start=1):
        out.write(f"  {index}. {setup.name:<18} {setup.summary}\n")
    while True:
        answer = ask(f"Choose 1-{len(PROTOCOLS)}: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(PROTOCOLS):
            return PROTOCOLS[int(answer) - 1]
        chosen = protocol_setup(answer)
        if chosen is not None:
            return chosen
        out.write("Please enter one of the numbers above.\n")


def _tracked_by_git(path: Path) -> bool:
    """True when ``path`` is inside a git work tree and not ignored by it."""
    git = shutil.which("git")
    if git is None:
        return False
    inside = subprocess.run(
        [git, "rev-parse", "--is-inside-work-tree"],
        cwd=path.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if inside.returncode != 0:
        return False
    ignored = subprocess.run(
        [git, "check-ignore", "-q", path.name],
        cwd=path.parent,
        capture_output=True,
        check=False,
    )
    return ignored.returncode != 0


# ---------------------------------------------------------------------------
# atlas doctor
# ---------------------------------------------------------------------------


def run_doctor(command: DoctorCommand, *, use_unicode: bool) -> tuple[str, bool]:
    """Return the rendered report and whether every check passed."""
    report = diagnose(live=command.live)
    return render_report(report, use_unicode=use_unicode), report.ok


def render_report(report: ConfigurationReport, *, use_unicode: bool) -> str:
    """Render a configuration report as aligned lines with fixes beneath."""
    width = max(len(check.name) for check in report.checks)
    lines = ["ATLAS configuration", ""]
    for check in report.checks:
        mark = _STATUS_MARKS[check.status][0 if use_unicode else 1]
        lines.append(f"  {mark:<4} {check.name:<{width}}  {check.detail}")
        if check.fix and check.status != CheckStatus.OK:
            lines.append(f"  {'':<4} {'':<{width}}  -> {check.fix}")
    lines.append("")
    if not report.ok:
        lines.append("Fix the items marked above, then run 'atlas doctor' again.")
    elif any(check.name == "Live request" for check in report.checks):
        lines.append("Ready.")
    else:
        lines.append("Ready. Run 'atlas doctor --live' to send one test request.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# atlas demo
# ---------------------------------------------------------------------------

_DEMO_ENVIRONMENT = {
    "ATLAS_AI_PROTOCOL": "SCRIPTED",
    "ATLAS_EMBEDDING_ENABLED": "false",
    "ATLAS_INSTRUMENTATION_ENABLED": "false",
}


def run_demo(_command: DemoCommand, *, out: TextIO) -> str:
    """Take a throwaway project through every AI stage, offline.

    Environment variables take precedence over ``.env``, so this overrides
    the user's configuration for this process only and never touches their
    files or workspace.
    """
    workspace = make_demo_workspace()
    os.environ.update(_DEMO_ENVIRONMENT)
    os.environ["ATLAS_WORKSPACE_ROOT"] = str(workspace)
    platform = atlas_eng.create()

    out.write(
        "ATLAS demo -- offline, using built-in canned proposals (no AI model).\n\n"
    )
    project = platform.create_project(
        CreateProjectCommand(
            name="Demo Project",
            description="A throwaway project to show the ATLAS workflow.",
            objective="Take an idea from research to a reviewed design.",
        )
    )
    out.write(f"Created project '{project.name}'.\n")
    platform.transition_stage(
        TransitionStageCommand(project_id=project.id, reason="Start the demo.")
    )
    for stage, field in _HEADLINES.items():
        proposal = platform.execute_stage(
            ExecuteStageCommand(project_id=project.id, stage=stage)
        )
        headline = str(proposal.content.get(field, "")).strip()
        out.write(f"\n[{stage.value}] Proposal drafted:\n  {headline}\n")
        result = platform.approve_proposal(
            ApproveProposalCommand(project_id=project.id, proposal_id=proposal.id)
        )
        if not result.success:
            raise OnboardingError(f"Demo approval failed: {result.patch_summary}")
        out.write("  You approved it; it is now part of the project record.\n")

    knowledge = platform.list_knowledge_candidates(
        ListKnowledgeCandidatesCommand(project_id=project.id)
    )
    project_dir = next(workspace.iterdir())
    return "\n".join(
        [
            "",
            f"Extracted {len(knowledge.candidates)} engineering-knowledge "
            "candidates for review.",
            "",
            f"Everything is in {project_dir}",
            f"  Readable proposals: {project_dir / 'atlas-proposals' / 'approved'}",
            "  This is a temporary directory; nothing in your own workspace changed.",
            "",
            "Next: run 'atlas init' to connect a real AI model, then "
            "'atlas doctor' to check it.",
        ]
    )
