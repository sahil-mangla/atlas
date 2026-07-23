"""Renders an AIProposal as human-readable Markdown for repo-native review.

Deliberately independent of ``presentation.renderers`` -- that renderer family
targets presentation read-model views (which carry a ``kind`` field AIProposal
does not have), and ``engine.*`` must not import ``presentation.*``.
"""

from typing import Any

from engine.domain.ai import AIProposal


def _title(key: str) -> str:
    return key.replace("_", " ").title()


def _render_value(key: str, value: Any, level: int) -> list[str]:
    heading = "#" * level
    if isinstance(value, dict):
        lines = [f"{heading} {_title(key)}"]
        for k, v in value.items():
            lines.extend(_render_value(k, v, level + 1))
        return lines
    if isinstance(value, list):
        lines = [f"{heading} {_title(key)}"]
        if not value:
            lines.append("- _none_")
            return lines
        for item in value:
            if isinstance(item, dict):
                lines.append("---")
                for k, v in item.items():
                    lines.extend(_render_value(k, v, level + 1))
            else:
                lines.append(f"- {item}")
        return lines
    return [f"**{_title(key)}**: {value}"]


def render_proposal_markdown(proposal: AIProposal[Any]) -> str:
    """Render a proposal for human review as a standalone Markdown document."""
    data = (
        proposal.data.model_dump(mode="json")
        if hasattr(proposal.data, "model_dump")
        else proposal.data
    )

    lines = [
        f"# {proposal.proposal_type.value.title()} Proposal",
        "",
        f"**Proposal ID**: {proposal.id}",
        f"**Status**: {proposal.status.value}",
        f"**Prompt version**: {proposal.prompt_metadata.version}",
        "",
    ]
    for key, value in data.items():
        lines.extend(_render_value(key, value, 2))
        lines.append("")

    if proposal.human_feedback:
        lines.append("## Human Feedback")
        lines.append(proposal.human_feedback)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
