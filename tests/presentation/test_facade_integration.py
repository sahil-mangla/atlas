"""Facade integration tests: the full Phase 14 pipeline end-to-end.

    Atlas -> Read Model -> Collector -> Immutable View -> Renderer -> RenderResult

Exercised through the public Atlas facade only, against a real (filesystem,
tmp_path-backed) platform instance -- proving the presentation layer is
actually wired and functional, not just unit-correct in isolation.
"""

import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import atlas as atlas_pkg
from atlas._service import Atlas
from atlas.commands import CreateProjectCommand
from atlas.exceptions import ApplicationError, ProjectNotFoundError
from engine.config import Settings
from presentation.renderers import RenderContract
from presentation.views import DiagnosticsView, ProjectDashboardView
from tests.support.test_bootstrap import create_test_platform

AtlasWithProject = tuple[Atlas, UUID]


@pytest.fixture
def atlas_with_project(tmp_path: Path) -> AtlasWithProject:
    atlas = create_test_platform(tmp_path)
    result = atlas.create_project(
        CreateProjectCommand(name="Atlas", description="d", objective="Ship Phase 14")
    )
    return atlas, result.id


def test_project_dashboard_view_reflects_created_project(
    atlas_with_project: AtlasWithProject,
) -> None:
    atlas, project_id = atlas_with_project
    view = atlas.get_project_dashboard_view(project_id)
    assert isinstance(view, ProjectDashboardView)
    assert view.project_id == project_id
    assert view.title == "Atlas"
    assert view.status.label == "initialized"


def test_workflow_status_view_reflects_initial_workflow(
    atlas_with_project: AtlasWithProject,
) -> None:
    atlas, project_id = atlas_with_project
    view = atlas.get_workflow_status_view(project_id)
    assert view.project_id == project_id
    assert view.stage == "idea"


def test_research_summary_view_for_project_without_research(
    atlas_with_project: AtlasWithProject,
) -> None:
    atlas, project_id = atlas_with_project
    view = atlas.get_research_summary_view(project_id)
    assert view.exists is False


def test_knowledge_summary_view_for_project_without_knowledge(
    atlas_with_project: AtlasWithProject,
) -> None:
    atlas, project_id = atlas_with_project
    view = atlas.get_knowledge_summary_view(project_id)
    assert view.metrics[0].value == 0 or all(m.value == 0 for m in view.metrics)


def test_diagnostics_view_reports_missing_subsystems(
    atlas_with_project: AtlasWithProject,
) -> None:
    atlas, project_id = atlas_with_project
    view = atlas.get_diagnostics_view(project_id)
    assert isinstance(view, DiagnosticsView)
    assert view.healthy is False
    assert "Research not started." in view.issues


def test_full_pipeline_view_to_render_json(
    atlas_with_project: AtlasWithProject,
) -> None:
    atlas, project_id = atlas_with_project
    view = atlas.get_project_dashboard_view(project_id)
    result = atlas.render(view, renderer="json")
    assert result.media_type == "application/json"
    parsed = json.loads(result.content)
    assert parsed["title"] == "Atlas"


def test_full_pipeline_view_to_render_markdown(
    atlas_with_project: AtlasWithProject,
) -> None:
    atlas, project_id = atlas_with_project
    view = atlas.get_diagnostics_view(project_id)
    result = atlas.render(view, renderer="markdown")
    assert result.media_type == "text/markdown"
    assert result.content.startswith("# Diagnostics")


def test_full_pipeline_view_to_render_cli(atlas_with_project: AtlasWithProject) -> None:
    atlas, project_id = atlas_with_project
    view = atlas.get_workflow_status_view(project_id)
    result = atlas.render(view, renderer="cli")
    assert result.media_type == "text/plain"


def test_render_accepts_explicit_contract(atlas_with_project: AtlasWithProject) -> None:
    atlas, project_id = atlas_with_project
    view = atlas.get_project_dashboard_view(project_id)
    result = atlas.render(
        view, renderer="json", contract=RenderContract(schema_version="2")
    )
    parsed = json.loads(result.content)
    assert result.metadata["schema_version"] == "2"
    assert parsed["title"] == "Atlas"


def test_render_unknown_renderer_raises(atlas_with_project: AtlasWithProject) -> None:
    """An unknown renderer name must surface as an ApplicationError (the
    only exception type CLI/MCP/REST callers catch at the boundary), not a
    bare ValueError that would escape uncaught."""
    atlas, project_id = atlas_with_project
    view = atlas.get_project_dashboard_view(project_id)
    with pytest.raises(ApplicationError, match="Unknown renderer"):
        atlas.render(view, renderer="xml")


def test_get_project_dashboard_view_for_unknown_project_raises(tmp_path: Path) -> None:
    atlas = create_test_platform(tmp_path)
    with pytest.raises(ProjectNotFoundError):
        atlas.get_project_dashboard_view(uuid4())


def test_atlas_created_via_atlas_create_has_working_presentation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real public entrypoint (atlas.create()) -- not just the test
    helper -- must also have presentation fully wired."""

    def fake_get_settings() -> Settings:
        return Settings(
            workspace_root=tmp_path / "workspace",
            ai_protocol="OLLAMA",
            ai_endpoint="http://localhost:11434",
            ai_model="llama3",
            ai_api_key=None,
        )

    monkeypatch.setattr("atlas._bootstrap.get_settings", fake_get_settings)
    real_atlas = atlas_pkg.create()
    result = real_atlas.create_project(
        CreateProjectCommand(name="Real", description="d", objective="o")
    )
    view = real_atlas.get_project_dashboard_view(result.id)
    rendered = real_atlas.render(view, renderer="cli")
    assert rendered.content
    assert rendered.media_type == "text/plain"
