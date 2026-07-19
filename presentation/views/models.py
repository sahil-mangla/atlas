"""Fully computed, ephemeral, deeply immutable presentation views."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from presentation.components import Metric, Section, StatusBadge


class View(BaseModel):
    model_config = ConfigDict(frozen=True)


class ProjectDashboardView(View):
    kind: Literal["project_dashboard"] = "project_dashboard"
    project_id: UUID
    title: str
    status: StatusBadge
    sections: tuple[Section, ...] = ()
    metrics: tuple[Metric, ...] = ()


class WorkflowStatusView(View):
    kind: Literal["workflow_status"] = "workflow_status"
    project_id: UUID
    stage: str
    readiness: StatusBadge
    objectives: tuple[str, ...] = ()
    blocking_issues: tuple[str, ...] = ()


class ResearchSummaryView(View):
    kind: Literal["research_summary"] = "research_summary"
    project_id: UUID
    exists: bool
    metrics: tuple[Metric, ...] = ()
    summary: Section


class KnowledgeSummaryView(View):
    kind: Literal["knowledge_summary"] = "knowledge_summary"
    project_id: UUID
    metrics: tuple[Metric, ...] = ()
    published_titles: tuple[str, ...] = ()


class DiagnosticsView(View):
    kind: Literal["diagnostics"] = "diagnostics"
    project_id: UUID
    healthy: bool
    status: StatusBadge
    issues: tuple[str, ...] = ()


PresentationView = Annotated[
    ProjectDashboardView
    | WorkflowStatusView
    | ResearchSummaryView
    | KnowledgeSummaryView
    | DiagnosticsView,
    Field(discriminator="kind"),
]
