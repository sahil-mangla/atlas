"""View collectors. Components are assembled by views, never by components."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from presentation.components import Metric, Section, StatusBadge
from presentation.views import (
    DiagnosticsView,
    KnowledgeSummaryView,
    ProjectDashboardView,
    ResearchSummaryView,
    WorkflowStatusView,
)

if TYPE_CHECKING:
    # Public facade import only, for type checking. Avoided at runtime because
    # atlas._service imports presentation.read_models/views/orchestration at
    # module scope; a runtime import here would be circular.
    from atlas import Atlas


class ProjectDashboardCollector:
    def __init__(self, atlas: Atlas) -> None:
        self.atlas = atlas

    def collect(self, project_id: UUID) -> ProjectDashboardView:
        project = self.atlas.get_project_read_model(project_id)
        workflow = self.atlas.get_workflow_read_model(project_id)
        research = self.atlas.get_research_read_model(project_id)
        knowledge = self.atlas.get_knowledge_read_model(project_id)
        return ProjectDashboardView(
            project_id=project.id,
            title=project.name,
            status=StatusBadge(
                label=project.status, positive=project.status != "archived"
            ),
            sections=(Section(title="Objective", body=project.objective),),
            metrics=(
                Metric(label="Workflow stage", value=workflow.current_stage),
                Metric(label="Research findings", value=research.finding_count),
                Metric(label="Published knowledge", value=knowledge.published_count),
            ),
        )


class WorkflowStatusCollector:
    def __init__(self, atlas: Atlas) -> None:
        self.atlas = atlas

    def collect(self, project_id: UUID) -> WorkflowStatusView:
        model = self.atlas.get_workflow_read_model(project_id)
        return WorkflowStatusView(
            project_id=project_id,
            stage=model.current_stage,
            readiness=StatusBadge(
                label=model.readiness_status, positive=model.is_ready
            ),
            objectives=model.objectives,
            blocking_issues=model.blocking_issues,
        )


class ResearchSummaryCollector:
    def __init__(self, atlas: Atlas) -> None:
        self.atlas = atlas

    def collect(self, project_id: UUID) -> ResearchSummaryView:
        model = self.atlas.get_research_read_model(project_id)
        return ResearchSummaryView(
            project_id=project_id,
            exists=model.exists,
            metrics=(
                Metric(label="Sources", value=model.source_count),
                Metric(label="Findings", value=model.finding_count),
                Metric(label="Opportunities", value=model.opportunity_count),
                Metric(label="Open questions", value=model.open_question_count),
            ),
            summary=Section(
                title="Latest summary", body=model.latest_summary or "None"
            ),
        )


class KnowledgeSummaryCollector:
    def __init__(self, atlas: Atlas) -> None:
        self.atlas = atlas

    def collect(self, project_id: UUID) -> KnowledgeSummaryView:
        model = self.atlas.get_knowledge_read_model(project_id)
        return KnowledgeSummaryView(
            project_id=project_id,
            metrics=(
                Metric(label="Candidates", value=model.candidate_count),
                Metric(label="Pending review", value=model.pending_candidate_count),
                Metric(label="Published", value=model.published_count),
                Metric(label="Active", value=model.active_published_count),
            ),
            published_titles=model.published_titles,
        )


class DiagnosticsCollector:
    def __init__(self, atlas: Atlas) -> None:
        self.atlas = atlas

    def collect(self, project_id: UUID) -> DiagnosticsView:
        model = self.atlas.get_diagnostics_read_model(project_id)
        return DiagnosticsView(
            project_id=project_id,
            healthy=not model.issues,
            status=StatusBadge(
                label="healthy" if not model.issues else "issues",
                positive=not model.issues,
            ),
            issues=model.issues,
        )
