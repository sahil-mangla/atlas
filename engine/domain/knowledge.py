"""Domain models for reviewed, project-scoped engineering knowledge."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from engine.domain.enums import (
    KnowledgeActorType,
    KnowledgeCandidateStatus,
    KnowledgeCategory,
    KnowledgeScope,
    KnowledgeSourceType,
    PublishedKnowledgeStatus,
    WorkflowStage,
)
from engine.domain.traceability import TraceabilityLink


class KnowledgeActor(BaseModel):
    actor_type: KnowledgeActorType
    actor_id: str
    display_name: str = ""


class KnowledgeProvenance(BaseModel):
    source_type: KnowledgeSourceType
    source_id: UUID
    source_description: str = ""
    extracted_at: datetime
    actor: KnowledgeActor


class KnowledgeRetrievalQuery(BaseModel):
    scope: KnowledgeScope = KnowledgeScope.PROJECT
    project_id: UUID | None = None
    workspace_id: UUID | None = None
    stage: WorkflowStage | None = None
    categories: list[KnowledgeCategory] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    max_entries: int = 20

    @model_validator(mode="after")
    def project_scope_only(self) -> "KnowledgeRetrievalQuery":
        if self.scope != KnowledgeScope.PROJECT:
            raise ValueError("Only project-scoped knowledge is supported in ATLAS v1.")
        return self


class EngineeringKnowledgeContext(BaseModel):
    entry_ids: list[UUID] = Field(default_factory=list)
    serialized_section: str = "## Engineering Knowledge\nNone\n"
    scope: KnowledgeScope = KnowledgeScope.PROJECT


class HumanKnowledgeSubmission(BaseModel):
    title: str
    content: str
    category: KnowledgeCategory
    tags: list[str] = Field(default_factory=list)
    actor: KnowledgeActor


class DeduplicationResult(BaseModel):
    is_exact_duplicate: bool = False
    is_near_duplicate: bool = False
    matching_published_id: UUID | None = None
    matching_candidate_id: UUID | None = None
    normalized_fingerprint: str


class KnowledgeCandidate(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    content: str
    category: KnowledgeCategory
    tags: list[str] = Field(default_factory=list)
    rationale: str = ""
    provenance: KnowledgeProvenance
    status: KnowledgeCandidateStatus = KnowledgeCandidateStatus.PENDING_REVIEW
    author: KnowledgeActor
    review_comment: str | None = None
    reviewed_by: KnowledgeActor | None = None
    traceability_links: list[TraceabilityLink] = Field(default_factory=list)
    deduplication_fingerprint: str = ""
    similar_to_published_id: UUID | None = None
    created_at: datetime

    def is_pending(self) -> bool:
        return self.status == KnowledgeCandidateStatus.PENDING_REVIEW

    def is_terminal(self) -> bool:
        return self.status in {
            KnowledgeCandidateStatus.REJECTED,
            KnowledgeCandidateStatus.WITHDRAWN,
        }


class PublishedKnowledge(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: UUID
    project_id: UUID
    title: str
    content: str
    category: KnowledgeCategory
    tags: list[str] = Field(default_factory=list)
    version: int
    status: PublishedKnowledgeStatus = PublishedKnowledgeStatus.ACTIVE
    provenance: KnowledgeProvenance
    traceability_links: list[TraceabilityLink] = Field(default_factory=list)
    author: KnowledgeActor
    published_at: datetime
    supersedes_id: UUID | None = None
    superseded_by_id: UUID | None = None
    candidate_id: UUID
    deduplication_fingerprint: str
    scope: KnowledgeScope = KnowledgeScope.PROJECT


class KnowledgePersistenceDocument(BaseModel):
    """Serialization-only envelope for ``.atlas/knowledge.json``."""

    project_id: UUID
    candidates: list[KnowledgeCandidate] = Field(default_factory=list)
    published: list[PublishedKnowledge] = Field(default_factory=list)
    schema_version: int = 1
