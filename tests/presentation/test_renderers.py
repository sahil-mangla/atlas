"""Renderer tests: formatting-only, deterministic, RenderResult contract."""

import dataclasses
import json
from types import MappingProxyType
from uuid import UUID

import pytest

from presentation.components import Metric, Section, StatusBadge
from presentation.renderers import RenderContract, RendererRegistry, RenderResult
from presentation.renderers.base import CliRenderer, JsonRenderer, MarkdownRenderer
from presentation.views import ProjectDashboardView

PROJECT_ID = UUID("00000000-0000-0000-0000-000000000001")


def _dashboard_view() -> ProjectDashboardView:
    return ProjectDashboardView(
        project_id=PROJECT_ID,
        title="Test",
        status=StatusBadge(label="initialized", positive=True),
        sections=(Section(title="Objective", body="Ship it"),),
        metrics=(Metric(label="Stage", value="idea"),),
    )


def test_render_result_is_frozen_dataclass() -> None:
    result = RenderResult(
        content="x", media_type="text/plain", renderer="cli", metadata={}
    )
    assert dataclasses.is_dataclass(result)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.content = "y"  # type: ignore[misc]


def test_render_result_metadata_is_immutable_mapping() -> None:
    result = RenderResult(
        content="x", media_type="text/plain", renderer="cli", metadata={"a": 1}
    )
    assert isinstance(result.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        result.metadata["a"] = 2  # type: ignore[index]


def test_json_renderer_returns_render_result_with_correct_media_type() -> None:
    result = JsonRenderer().render(_dashboard_view(), RenderContract())
    assert isinstance(result, RenderResult)
    assert result.media_type == "application/json"
    assert result.renderer == "json"


def test_json_renderer_is_deterministic() -> None:
    view = _dashboard_view()
    r1 = JsonRenderer().render(view, RenderContract())
    r2 = JsonRenderer().render(view, RenderContract())
    assert r1.content == r2.content


def test_json_renderer_output_is_valid_json() -> None:
    result = JsonRenderer().render(_dashboard_view(), RenderContract())
    parsed = json.loads(result.content)
    assert parsed["kind"] == "project_dashboard"
    assert parsed["title"] == "Test"


def test_markdown_renderer_returns_correct_media_type() -> None:
    result = MarkdownRenderer().render(_dashboard_view(), RenderContract())
    assert result.media_type == "text/markdown"
    assert result.renderer == "markdown"


def test_markdown_renderer_formats_list_of_dicts_without_raw_repr() -> None:
    result = MarkdownRenderer().render(_dashboard_view(), RenderContract())
    assert "{'title'" not in result.content
    assert "{'label'" not in result.content
    assert "**title**: Objective" in result.content


def test_markdown_renderer_honors_include_titles_false() -> None:
    result = MarkdownRenderer().render(
        _dashboard_view(), RenderContract(include_titles=False)
    )
    assert not result.content.startswith("# ")


def test_cli_renderer_returns_plain_text() -> None:
    result = CliRenderer().render(_dashboard_view(), RenderContract())
    assert result.media_type == "text/plain"
    assert result.renderer == "cli"
    assert "# " not in result.content


def test_cli_renderer_is_deterministic() -> None:
    view = _dashboard_view()
    r1 = CliRenderer().render(view, RenderContract())
    r2 = CliRenderer().render(view, RenderContract())
    assert r1.content == r2.content


def test_renderers_never_reference_atlas_or_engine() -> None:
    import presentation.renderers.base as mod

    source = mod.__file__
    assert source is not None
    with open(source) as f:
        content = f.read()
    assert "atlas" not in content.lower()
    assert "engine" not in content.lower()


def test_renderer_registry_resolves_by_name() -> None:
    registry = RendererRegistry((JsonRenderer(), MarkdownRenderer(), CliRenderer()))
    assert registry.resolve("json").name == "json"
    assert registry.resolve("markdown").name == "markdown"
    assert registry.resolve("cli").name == "cli"


def test_renderer_registry_raises_for_unknown_renderer() -> None:
    registry = RendererRegistry((JsonRenderer(),))
    with pytest.raises(ValueError, match="Unknown renderer"):
        registry.resolve("xml")
