"""Presentation orchestration that produces views only.

Collectors are received through constructor injection; the composition root
(atlas/_bootstrap.py) is responsible for constructing them. This service
coordinates collector selection only and never constructs its collaborators.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from presentation.views import (
    DiagnosticsView,
    KnowledgeSummaryView,
    ProjectDashboardView,
    ResearchSummaryView,
    WorkflowStatusView,
)

if TYPE_CHECKING:
    from presentation.collectors.collectors import (
        DiagnosticsCollector,
        KnowledgeSummaryCollector,
        ProjectDashboardCollector,
        ResearchSummaryCollector,
        WorkflowStatusCollector,
    )


class PlatformOrchestrationService:
    def __init__(
        self,
        project_dashboard: ProjectDashboardCollector,
        workflow_status: WorkflowStatusCollector,
        research_summary: ResearchSummaryCollector,
        knowledge_summary: KnowledgeSummaryCollector,
        diagnostics: DiagnosticsCollector,
    ) -> None:
        self.project_dashboard = project_dashboard
        self.workflow_status = workflow_status
        self.research_summary = research_summary
        self.knowledge_summary = knowledge_summary
        self.diagnostics = diagnostics

    def get_project_dashboard_view(self, project_id: UUID) -> ProjectDashboardView:
        return self.project_dashboard.collect(project_id)

    def get_workflow_status_view(self, project_id: UUID) -> WorkflowStatusView:
        return self.workflow_status.collect(project_id)

    def get_research_summary_view(self, project_id: UUID) -> ResearchSummaryView:
        return self.research_summary.collect(project_id)

    def get_knowledge_summary_view(self, project_id: UUID) -> KnowledgeSummaryView:
        return self.knowledge_summary.collect(project_id)

    def get_diagnostics_view(self, project_id: UUID) -> DiagnosticsView:
        return self.diagnostics.collect(project_id)
