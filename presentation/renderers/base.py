import json
from typing import Any

from presentation.renderers.contract import RenderContract
from presentation.renderers.result import RenderResult


def _data(view: Any) -> dict[str, Any]:
    result: dict[str, Any] = view.model_dump(mode="json")
    return result


class JsonRenderer:
    name = "json"

    def render(self, view: Any, contract: RenderContract) -> RenderResult:
        return RenderResult(
            content=json.dumps(_data(view), indent=2, sort_keys=True) + "\n",
            media_type="application/json",
            renderer=self.name,
            metadata={
                "schema_version": contract.schema_version,
                "view_kind": view.kind,
            },
        )


def _format_list_item(item: Any) -> str:
    if isinstance(item, dict):
        return ", ".join(f"**{k}**: {v}" for k, v in item.items())
    return str(item)


class MarkdownRenderer:
    name = "markdown"

    def render(self, view: Any, contract: RenderContract) -> RenderResult:
        data = _data(view)
        title = data["kind"].replace("_", " ").title()
        lines = [f"# {title}"] if contract.include_titles else []
        for key, value in data.items():
            if key == "kind":
                continue
            if isinstance(value, list):
                lines.append(f"## {key.replace('_', ' ').title()}")
                lines.extend(f"- {_format_list_item(item)}" for item in value)
            elif isinstance(value, dict):
                lines.append(f"## {key.replace('_', ' ').title()}")
                lines.extend(f"- **{k}**: {v}" for k, v in value.items())
            else:
                lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
        return RenderResult(
            content="\n".join(lines) + "\n",
            media_type="text/markdown",
            renderer=self.name,
            metadata={
                "schema_version": contract.schema_version,
                "view_kind": view.kind,
            },
        )


def _strip_markdown_headers(content: str) -> str:
    """Strip leading `# `/`## ` markers per line without corrupting `## `
    (a naive chained str.replace eats the `# ` inside `## ` first)."""
    lines = []
    for line in content.split("\n"):
        if line.startswith("## "):
            lines.append("\n" + line[3:])
        elif line.startswith("# "):
            lines.append(line[2:])
        else:
            lines.append(line)
    return "\n".join(lines)


class CliRenderer(MarkdownRenderer):
    name = "cli"

    def render(self, view: Any, contract: RenderContract) -> RenderResult:
        result = super().render(view, contract)
        return RenderResult(
            content=_strip_markdown_headers(result.content),
            media_type="text/plain",
            renderer=self.name,
            metadata=result.metadata,
        )
