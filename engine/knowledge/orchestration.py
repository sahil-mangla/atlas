from typing import Any
from uuid import UUID

from engine.domain.ai_drafts import KnowledgeCandidateDraft
from engine.domain.enums import KnowledgeSourceType, ProposalDecision, WorkflowStage
from engine.domain.knowledge import (
    EngineeringKnowledgeContext,
    HumanKnowledgeSubmission,
    KnowledgeActor,
    KnowledgeCandidate,
    PublishedKnowledge,
)
from engine.knowledge.extractors.base import ExtractorRegistry
from engine.knowledge.services import (
    KnowledgeApprovalService,
    KnowledgeCandidateService,
    KnowledgeLifecycleService,
    KnowledgeRetrievalService,
)


class KnowledgeOrchestrationService:
    """The sole public boundary of the knowledge subsystem."""
    def __init__(self, candidates: KnowledgeCandidateService, approval: KnowledgeApprovalService, retrieval: KnowledgeRetrievalService, lifecycle: KnowledgeLifecycleService, extractors: ExtractorRegistry) -> None:
        self.candidates, self.approval, self.retrieval, self.lifecycle, self.extractors = candidates, approval, retrieval, lifecycle, extractors

    def retrieve_for_stage(self, project_id: UUID, stage: WorkflowStage) -> EngineeringKnowledgeContext:
        return self.retrieval.retrieve_for_stage(project_id, stage)

    def submit_candidate(self, project_id: UUID, submission: HumanKnowledgeSubmission) -> KnowledgeCandidate | None:
        return self.candidates.create_from_submission(project_id, submission)

    def list_pending_candidates(self, project_id: UUID) -> list[KnowledgeCandidate]:
        return self.candidates.get_pending(project_id)

    def process_candidate_review(self, project_id: UUID, candidate_id: UUID, decision: ProposalDecision, actor: KnowledgeActor, feedback: str | None = None) -> PublishedKnowledge | KnowledgeCandidate:
        if decision == ProposalDecision.APPROVE:
            return self.approval.approve_and_publish(project_id, candidate_id, actor, feedback)
        return self.approval.reject(project_id, candidate_id, actor, feedback)

    def extract_candidate_from_artifact(self, project_id: UUID, source_type: KnowledgeSourceType, source_id: UUID) -> None:
        candidates = self.extractors.extract(project_id, source_type, source_id)
        for candidate in candidates:
            self.candidates.create(candidate)

    def create_candidate_from_ai_proposal(self, project_id: UUID, draft: KnowledgeCandidateDraft, actor: KnowledgeActor) -> KnowledgeCandidate | None:
        return self.candidates.create_from_ai_draft(project_id, draft, actor)

    def import_candidates(self, project_id: UUID, bundle: list[dict[str, Any]], actor: KnowledgeActor) -> list[KnowledgeCandidate]:
        created = []
        for entry in bundle:
            res = self.candidates.create_from_import(project_id, entry, actor)
            if res:
                created.append(res)
        return created

    def supersede_knowledge(self, project_id: UUID, old_id: UUID, new_published: PublishedKnowledge) -> PublishedKnowledge:
        return self.lifecycle.supersede(project_id, old_id, new_published)

    def deprecate_knowledge(self, project_id: UUID, entry_id: UUID, reason: str, actor: KnowledgeActor) -> PublishedKnowledge:
        return self.lifecycle.deprecate(project_id, entry_id, reason, actor)
