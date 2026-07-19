"""Immutable, public read models used by Phase 14 collectors."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReadModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class ProjectReadModel(ReadModel):
    id: UUID
    name: str
    description: str
    objective: str
    status: str


class WorkflowReadModel(ReadModel):
    project_id: UUID
    current_stage: str
    readiness_status: str
    is_ready: bool
    objectives: tuple[str, ...] = ()
    blocking_issues: tuple[str, ...] = ()
    pending_knowledge_candidates: tuple[UUID, ...] = ()


class ResearchReadModel(ReadModel):
    project_id: UUID
    exists: bool
    source_count: int = 0
    finding_count: int = 0
    opportunity_count: int = 0
    open_question_count: int = 0
    latest_summary: str = ""


class KnowledgeReadModel(ReadModel):
    project_id: UUID
    candidate_count: int = 0
    pending_candidate_count: int = 0
    published_count: int = 0
    active_published_count: int = 0
    published_titles: tuple[str, ...] = ()


class DiagnosticsReadModel(ReadModel):
    project_id: UUID
    workflow_exists: bool
    research_exists: bool
    planning_exists: bool
    architecture_exists: bool
    evaluation_exists: bool
    knowledge_exists: bool
    issues: tuple[str, ...] = Field(default_factory=tuple)
