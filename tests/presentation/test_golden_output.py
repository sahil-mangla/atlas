"""Golden-output tests: stable, deterministic rendering for every view kind
across every renderer (CLI, JSON, Markdown).

Fixtures use a fixed UUID so output is byte-for-byte reproducible. If a
renderer's output format changes intentionally, update the golden string in
the same commit as the renderer change.
"""

from uuid import UUID

from presentation.components import Metric, Section, StatusBadge
from presentation.renderers import RenderContract
from presentation.renderers.base import CliRenderer, JsonRenderer, MarkdownRenderer
from presentation.views import (
    DiagnosticsView,
    KnowledgeSummaryView,
    ProjectDashboardView,
    ResearchSummaryView,
    WorkflowStatusView,
)

PID = UUID("11111111-1111-1111-1111-111111111111")
CONTRACT = RenderContract()

VIEWS = {
    "project_dashboard": ProjectDashboardView(
        project_id=PID,
        title="Atlas",
        status=StatusBadge(label="initialized", positive=True),
        sections=(Section(title="Objective", body="Ship it"),),
        metrics=(Metric(label="Workflow stage", value="idea"),),
    ),
    "workflow_status": WorkflowStatusView(
        project_id=PID,
        stage="research",
        readiness=StatusBadge(label="passed", positive=True),
        objectives=("Define problem",),
        blocking_issues=(),
    ),
    "research_summary": ResearchSummaryView(
        project_id=PID,
        exists=True,
        metrics=(Metric(label="Sources", value=2),),
        summary=Section(title="Latest summary", body="Synthesis text"),
    ),
    "knowledge_summary": KnowledgeSummaryView(
        project_id=PID,
        metrics=(Metric(label="Published", value=1),),
        published_titles=("Pattern A",),
    ),
    "diagnostics": DiagnosticsView(
        project_id=PID,
        healthy=False,
        status=StatusBadge(label="issues", positive=False),
        issues=("Planning not started.",),
    ),
}

GOLDEN_JSON = {
    "project_dashboard": (
        "{\n"
        '  "kind": "project_dashboard",\n'
        '  "metrics": [\n'
        "    {\n"
        '      "label": "Workflow stage",\n'
        '      "value": "idea"\n'
        "    }\n"
        "  ],\n"
        '  "project_id": "11111111-1111-1111-1111-111111111111",\n'
        '  "sections": [\n'
        "    {\n"
        '      "body": "Ship it",\n'
        '      "title": "Objective"\n'
        "    }\n"
        "  ],\n"
        '  "status": {\n'
        '    "label": "initialized",\n'
        '    "positive": true\n'
        "  },\n"
        '  "title": "Atlas"\n'
        "}\n"
    ),
    "diagnostics": (
        "{\n"
        '  "healthy": false,\n'
        '  "issues": [\n'
        '    "Planning not started."\n'
        "  ],\n"
        '  "kind": "diagnostics",\n'
        '  "project_id": "11111111-1111-1111-1111-111111111111",\n'
        '  "status": {\n'
        '    "label": "issues",\n'
        '    "positive": false\n'
        "  }\n"
        "}\n"
    ),
}

GOLDEN_MARKDOWN = {
    "project_dashboard": (
        "# Project Dashboard\n"
        "- **Project Id**: 11111111-1111-1111-1111-111111111111\n"
        "- **Title**: Atlas\n"
        "## Status\n"
        "- **label**: initialized\n"
        "- **positive**: True\n"
        "## Sections\n"
        "- **title**: Objective, **body**: Ship it\n"
        "## Metrics\n"
        "- **label**: Workflow stage, **value**: idea\n"
    ),
    "diagnostics": (
        "# Diagnostics\n"
        "- **Project Id**: 11111111-1111-1111-1111-111111111111\n"
        "- **Healthy**: False\n"
        "## Status\n"
        "- **label**: issues\n"
        "- **positive**: False\n"
        "## Issues\n"
        "- Planning not started.\n"
    ),
}

GOLDEN_CLI = {
    "project_dashboard": (
        "Project Dashboard\n"
        "- **Project Id**: 11111111-1111-1111-1111-111111111111\n"
        "- **Title**: Atlas\n"
        "\nStatus\n"
        "- **label**: initialized\n"
        "- **positive**: True\n"
        "\nSections\n"
        "- **title**: Objective, **body**: Ship it\n"
        "\nMetrics\n"
        "- **label**: Workflow stage, **value**: idea\n"
    ),
}


def test_json_golden_project_dashboard() -> None:
    result = JsonRenderer().render(VIEWS["project_dashboard"], CONTRACT)
    assert result.content == GOLDEN_JSON["project_dashboard"]


def test_json_golden_diagnostics() -> None:
    result = JsonRenderer().render(VIEWS["diagnostics"], CONTRACT)
    assert result.content == GOLDEN_JSON["diagnostics"]


def test_markdown_golden_project_dashboard() -> None:
    result = MarkdownRenderer().render(VIEWS["project_dashboard"], CONTRACT)
    assert result.content == GOLDEN_MARKDOWN["project_dashboard"]


def test_markdown_golden_diagnostics() -> None:
    result = MarkdownRenderer().render(VIEWS["diagnostics"], CONTRACT)
    assert result.content == GOLDEN_MARKDOWN["diagnostics"]


def test_cli_golden_project_dashboard() -> None:
    result = CliRenderer().render(VIEWS["project_dashboard"], CONTRACT)
    assert result.content == GOLDEN_CLI["project_dashboard"]


def test_all_views_render_deterministically_across_all_renderers() -> None:
    """Every view kind renders identically across two independent calls,
    for every renderer -- the deterministic-rendering guarantee."""
    renderers = (JsonRenderer(), MarkdownRenderer(), CliRenderer())
    for view in VIEWS.values():
        for renderer in renderers:
            first = renderer.render(view, CONTRACT)
            second = renderer.render(view, CONTRACT)
            assert first.content == second.content
            assert first.media_type == second.media_type


def test_cli_renderer_does_not_corrupt_h2_markers() -> None:
    """Regression: a naive chained str.replace("# ", "").replace("## ", "\\n")
    eats the "# " inside "## " on the first call, leaving a stray "#" instead
    of a blank line before each section. The renderer must strip headers
    line-by-line instead."""
    result = CliRenderer().render(VIEWS["project_dashboard"], CONTRACT)
    assert "#Status" not in result.content
    assert "#Sections" not in result.content
    assert "#Metrics" not in result.content
    assert "\nStatus\n" in result.content


def test_every_view_kind_renders_without_error_on_every_renderer() -> None:
    renderers = (JsonRenderer(), MarkdownRenderer(), CliRenderer())
    for kind, view in VIEWS.items():
        for renderer in renderers:
            result = renderer.render(view, CONTRACT)
            assert result.content
            assert result.metadata["view_kind"] == kind
