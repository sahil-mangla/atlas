"""Collector tests: Atlas read APIs only, aggregate correctly, immutable views."""

from uuid import UUID, uuid4

from presentation.collectors.collectors import (
    DiagnosticsCollector,
    KnowledgeSummaryCollector,
    ProjectDashboardCollector,
    ResearchSummaryCollector,
    WorkflowStatusCollector,
)
from presentation.read_models import (
    DiagnosticsReadModel,
    KnowledgeReadModel,
    ProjectReadModel,
    ResearchReadModel,
    WorkflowReadModel,
)


class FakeAtlas:
    """A minimal stand-in exposing only the typed read-model API.

    If a collector ever calls anything beyond get_*_read_model, this fake
    raises AttributeError, proving collectors depend on nothing else.
    """

    def __init__(self, project_id: UUID) -> None:
        self.project_id = project_id

    def get_project_read_model(self, project_id: UUID) -> ProjectReadModel:
        return ProjectReadModel(
            id=project_id,
            name="Demo",
            description="desc",
            objective="objective",
            status="initialized",
        )

    def get_workflow_read_model(self, project_id: UUID) -> WorkflowReadModel:
        return WorkflowReadModel(
            project_id=project_id,
            current_stage="research",
            readiness_status="passed",
            is_ready=True,
            objectives=("Define problem",),
            blocking_issues=(),
        )

    def get_research_read_model(self, project_id: UUID) -> ResearchReadModel:
        return ResearchReadModel(
            project_id=project_id,
            exists=True,
            source_count=2,
            finding_count=3,
            opportunity_count=1,
            open_question_count=0,
            latest_summary="Synthesis",
        )

    def get_knowledge_read_model(self, project_id: UUID) -> KnowledgeReadModel:
        return KnowledgeReadModel(
            project_id=project_id,
            candidate_count=5,
            pending_candidate_count=2,
            published_count=3,
            active_published_count=3,
            published_titles=("Pattern A", "Pattern B"),
        )

    def get_diagnostics_read_model(self, project_id: UUID) -> DiagnosticsReadModel:
        return DiagnosticsReadModel(
            project_id=project_id,
            workflow_exists=True,
            research_exists=True,
            planning_exists=False,
            architecture_exists=False,
            evaluation_exists=False,
            knowledge_exists=False,
            issues=("Planning not started.",),
        )


def test_project_dashboard_collector_aggregates_across_read_models() -> None:
    project_id = uuid4()
    atlas = FakeAtlas(project_id)
    view = ProjectDashboardCollector(atlas).collect(project_id)  # type: ignore[arg-type]

    assert view.project_id == project_id
    assert view.title == "Demo"
    assert view.status.label == "initialized"
    assert view.status.positive is True
    metric_labels = {m.label: m.value for m in view.metrics}
    assert metric_labels["Workflow stage"] == "research"
    assert metric_labels["Research findings"] == 3
    assert metric_labels["Published knowledge"] == 3


def test_project_dashboard_collector_marks_archived_as_not_positive() -> None:
    project_id = uuid4()

    class ArchivedAtlas(FakeAtlas):
        def get_project_read_model(self, project_id: UUID) -> ProjectReadModel:
            return ProjectReadModel(
                id=project_id,
                name="Demo",
                description="d",
                objective="o",
                status="archived",
            )

    view = ProjectDashboardCollector(ArchivedAtlas(project_id)).collect(project_id)  # type: ignore[arg-type]
    assert view.status.positive is False


def test_workflow_status_collector_maps_readiness() -> None:
    project_id = uuid4()
    view = WorkflowStatusCollector(FakeAtlas(project_id)).collect(project_id)  # type: ignore[arg-type]
    assert view.stage == "research"
    assert view.readiness.positive is True
    assert view.objectives == ("Define problem",)


def test_research_summary_collector_aggregates_metrics() -> None:
    project_id = uuid4()
    view = ResearchSummaryCollector(FakeAtlas(project_id)).collect(project_id)  # type: ignore[arg-type]
    assert view.exists is True
    metric_labels = {m.label: m.value for m in view.metrics}
    assert metric_labels["Sources"] == 2
    assert metric_labels["Findings"] == 3
    assert view.summary.body == "Synthesis"


def test_research_summary_collector_defaults_missing_summary_to_none() -> None:
    project_id = uuid4()

    class NoSummaryAtlas(FakeAtlas):
        def get_research_read_model(self, project_id: UUID) -> ResearchReadModel:
            return ResearchReadModel(project_id=project_id, exists=False)

    view = ResearchSummaryCollector(NoSummaryAtlas(project_id)).collect(project_id)  # type: ignore[arg-type]
    assert view.summary.body == "None"


def test_knowledge_summary_collector_exposes_published_titles() -> None:
    project_id = uuid4()
    view = KnowledgeSummaryCollector(FakeAtlas(project_id)).collect(project_id)  # type: ignore[arg-type]
    assert view.published_titles == ("Pattern A", "Pattern B")
    metric_labels = {m.label: m.value for m in view.metrics}
    assert metric_labels["Pending review"] == 2


def test_diagnostics_collector_reports_unhealthy_when_issues_present() -> None:
    project_id = uuid4()
    view = DiagnosticsCollector(FakeAtlas(project_id)).collect(project_id)  # type: ignore[arg-type]
    assert view.healthy is False
    assert view.status.label == "issues"
    assert view.issues == ("Planning not started.",)


def test_diagnostics_collector_reports_healthy_when_no_issues() -> None:
    project_id = uuid4()

    class HealthyAtlas(FakeAtlas):
        def get_diagnostics_read_model(self, project_id: UUID) -> DiagnosticsReadModel:
            return DiagnosticsReadModel(
                project_id=project_id,
                workflow_exists=True,
                research_exists=True,
                planning_exists=True,
                architecture_exists=True,
                evaluation_exists=True,
                knowledge_exists=True,
                issues=(),
            )

    view = DiagnosticsCollector(HealthyAtlas(project_id)).collect(project_id)  # type: ignore[arg-type]
    assert view.healthy is True
    assert view.status.positive is True


def test_collectors_never_call_anything_beyond_read_model_api() -> None:
    """A fake exposing zero extra attributes still satisfies every collector."""
    project_id = uuid4()
    atlas = FakeAtlas(project_id)
    for collector_cls in (
        ProjectDashboardCollector,
        WorkflowStatusCollector,
        ResearchSummaryCollector,
        KnowledgeSummaryCollector,
        DiagnosticsCollector,
    ):
        collector_cls(atlas).collect(project_id)  # type: ignore[arg-type]
