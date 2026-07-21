"""View tests: deep immutability, component composition, no engine leakage."""

from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

import presentation.views.models as mod
from presentation.components import Metric, Section, StatusBadge
from presentation.views import (
    DiagnosticsView,
    KnowledgeSummaryView,
    ProjectDashboardView,
    ResearchSummaryView,
    WorkflowStatusView,
)


def test_project_dashboard_view_is_frozen() -> None:
    view = ProjectDashboardView(
        project_id=uuid4(),
        title="Test",
        status=StatusBadge(label="initialized", positive=True),
    )
    with pytest.raises(ValidationError):
        view.title = "Changed"


def test_project_dashboard_view_collections_are_immutable_tuples() -> None:
    view = ProjectDashboardView(
        project_id=uuid4(),
        title="Test",
        status=StatusBadge(label="initialized", positive=True),
        sections=(Section(title="Objective", body="Ship it"),),
        metrics=(Metric(label="Stage", value="idea"),),
    )
    assert isinstance(view.sections, tuple)
    assert isinstance(view.metrics, tuple)
    with pytest.raises((TypeError, AttributeError)):
        view.sections[0] = Section(title="x", body="y")  # type: ignore[index]


def test_workflow_status_view_deep_immutability() -> None:
    view = WorkflowStatusView(
        project_id=uuid4(),
        stage="idea",
        readiness=StatusBadge(label="ready", positive=True),
        objectives=("a", "b"),
        blocking_issues=(),
    )
    with pytest.raises(ValidationError):
        view.readiness = StatusBadge(label="not ready", positive=False)
    with pytest.raises(ValidationError):
        view.readiness.positive = False


def test_research_summary_view_requires_summary_section() -> None:
    view = ResearchSummaryView(
        project_id=uuid4(),
        exists=True,
        summary=Section(title="Latest summary", body="None"),
    )
    assert view.summary.body == "None"


def test_knowledge_summary_view_published_titles_is_tuple() -> None:
    view = KnowledgeSummaryView(project_id=uuid4(), published_titles=("A", "B"))
    assert view.published_titles == ("A", "B")
    assert isinstance(view.published_titles, tuple)


def test_diagnostics_view_defaults_to_empty_issues() -> None:
    view = DiagnosticsView(
        project_id=uuid4(),
        healthy=True,
        status=StatusBadge(label="healthy", positive=True),
    )
    assert view.issues == ()


def test_views_discriminated_by_kind() -> None:
    project_id = uuid4()
    view = DiagnosticsView(
        project_id=project_id,
        healthy=True,
        status=StatusBadge(label="healthy", positive=True),
    )
    assert view.kind == "diagnostics"


def test_view_module_has_no_atlas_or_engine_symbols() -> None:
    source = mod.__file__
    assert source is not None
    with Path(source).open() as f:
        content = f.read()
    assert "atlas" not in content.lower()
    assert "engine" not in content.lower()
