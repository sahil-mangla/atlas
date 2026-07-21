"""Business services for candidate review, publication, and retrieval."""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from engine.domain.ai_drafts import KnowledgeCandidateDraft
from engine.domain.enums import (
    KnowledgeActorType,
    KnowledgeCandidateStatus,
    KnowledgeCategory,
    KnowledgeScope,
    KnowledgeSourceType,
    PublishedKnowledgeStatus,
    WorkflowStage,
)
from engine.domain.knowledge import (
    DeduplicationResult,
    EngineeringKnowledgeContext,
    HumanKnowledgeSubmission,
    KnowledgeActor,
    KnowledgeCandidate,
    KnowledgeProvenance,
    KnowledgeRetrievalQuery,
    PublishedKnowledge,
)
from engine.knowledge.exceptions import KnowledgeReviewException
from engine.knowledge.profiles import STAGE_PROFILES
from engine.knowledge.repository import KnowledgeRepository


class KnowledgeDeduplicationService:
    @staticmethod
    def compute_fingerprint(
        title: str, content: str, category: object, tags: list[str]
    ) -> str:
        def normalize(value: str) -> str:
            return " ".join(value.lower().split())

        payload = "|".join(
            (
                normalize(title),
                normalize(content),
                str(category),
                ",".join(sorted(normalize(tag) for tag in tags)),
            )
        )
        return sha256(payload.encode()).hexdigest()

    def check(
        self,
        candidate: KnowledgeCandidate,
        published: list[PublishedKnowledge],
        pending: list[KnowledgeCandidate],
    ) -> DeduplicationResult:
        fingerprint = self.compute_fingerprint(
            candidate.title, candidate.content, candidate.category, candidate.tags
        )
        for entry in published:
            if (
                entry.status == PublishedKnowledgeStatus.ACTIVE
                and entry.deduplication_fingerprint == fingerprint
            ):
                return DeduplicationResult(
                    is_exact_duplicate=True,
                    matching_published_id=entry.id,
                    normalized_fingerprint=fingerprint,
                )
        for item in pending:
            if item.deduplication_fingerprint == fingerprint:
                return DeduplicationResult(
                    is_exact_duplicate=True,
                    matching_candidate_id=item.id,
                    normalized_fingerprint=fingerprint,
                )
        title = " ".join(candidate.title.lower().split())
        near = next(
            (
                entry
                for entry in published
                if entry.status == PublishedKnowledgeStatus.ACTIVE
                and entry.category == candidate.category
                and " ".join(entry.title.lower().split()) == title
            ),
            None,
        )
        return DeduplicationResult(
            is_near_duplicate=near is not None,
            matching_published_id=near.id if near else None,
            normalized_fingerprint=fingerprint,
        )


class KnowledgeCandidateService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        deduplication: KnowledgeDeduplicationService,
    ) -> None:
        self.repository, self.deduplication = repository, deduplication

    def create_from_submission(
        self, project_id: UUID, submission: HumanKnowledgeSubmission
    ) -> KnowledgeCandidate | None:
        now = datetime.now(UTC)
        candidate = KnowledgeCandidate(
            id=uuid4(),
            project_id=project_id,
            title=submission.title,
            content=submission.content,
            category=submission.category,
            tags=submission.tags,
            provenance=KnowledgeProvenance(
                source_type=KnowledgeSourceType.HUMAN_SUBMISSION,
                source_id=uuid4(),
                extracted_at=now,
                actor=submission.actor,
            ),
            author=submission.actor,
            created_at=now,
        )
        return self.create(candidate)

    def create_from_ai_draft(
        self, project_id: UUID, draft: KnowledgeCandidateDraft, actor: KnowledgeActor
    ) -> KnowledgeCandidate | None:
        now = datetime.now(UTC)
        candidate = KnowledgeCandidate(
            id=uuid4(),
            project_id=project_id,
            title=draft.title,
            content=draft.content,
            category=draft.category,
            tags=draft.tags,
            rationale=draft.rationale,
            provenance=KnowledgeProvenance(
                source_type=draft.source_snapshot_type
                or KnowledgeSourceType.AI_PROPOSAL,
                source_id=draft.source_snapshot_id or uuid4(),
                extracted_at=now,
                actor=actor,
            ),
            author=actor,
            created_at=now,
        )
        return self.create(candidate)

    def create_from_import(
        self, project_id: UUID, entry: dict[str, Any], actor: KnowledgeActor
    ) -> KnowledgeCandidate | None:
        now = datetime.now(UTC)
        candidate = KnowledgeCandidate(
            id=uuid4(),
            project_id=project_id,
            title=entry.get("title", "Imported Knowledge"),
            content=entry.get("content", ""),
            category=KnowledgeCategory(
                entry.get("category", KnowledgeCategory.LESSON_LEARNED)
            ),
            tags=entry.get("tags", []),
            rationale=entry.get("rationale", "Organizational Import"),
            provenance=KnowledgeProvenance(
                source_type=KnowledgeSourceType.ORGANIZATIONAL_IMPORT,
                source_id=uuid4(),
                extracted_at=now,
                actor=actor,
            ),
            author=actor,
            created_at=now,
        )
        return self.create(candidate)

    def create(self, candidate: KnowledgeCandidate) -> KnowledgeCandidate | None:
        result = self.deduplication.check(
            candidate,
            self.repository.list_published(candidate.project_id),
            self.get_pending(candidate.project_id),
        )
        if result.is_exact_duplicate:
            return None
        candidate.deduplication_fingerprint = result.normalized_fingerprint
        candidate.similar_to_published_id = (
            result.matching_published_id if result.is_near_duplicate else None
        )
        self.repository.save_candidate(candidate)
        return candidate

    def get_pending(self, project_id: UUID) -> list[KnowledgeCandidate]:
        return self.repository.list_candidates(
            project_id, KnowledgeCandidateStatus.PENDING_REVIEW
        )

    def withdraw(
        self, project_id: UUID, candidate_id: UUID, actor: KnowledgeActor
    ) -> KnowledgeCandidate:
        candidate = self.repository.get_candidate(project_id, candidate_id)
        if not candidate or not candidate.is_pending():
            raise KnowledgeReviewException("Only pending candidates may be withdrawn.")
        candidate.status, candidate.reviewed_by = (
            KnowledgeCandidateStatus.WITHDRAWN,
            actor,
        )
        self.repository.save_candidate(candidate)
        return candidate


class KnowledgeLifecycleService:
    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    def publish_from_candidate(
        self,
        candidate: KnowledgeCandidate,
        publisher: KnowledgeActor,  # noqa: ARG002 -- see Sprint 2 Code Quality Report finding
    ) -> PublishedKnowledge:
        entry = PublishedKnowledge(
            id=uuid4(),
            project_id=candidate.project_id,
            title=candidate.title,
            content=candidate.content,
            category=candidate.category,
            tags=candidate.tags,
            version=1,
            provenance=candidate.provenance,
            traceability_links=candidate.traceability_links,
            author=candidate.author,
            published_at=datetime.now(UTC),
            candidate_id=candidate.id,
            deduplication_fingerprint=candidate.deduplication_fingerprint,
        )
        self.repository.save_published(entry)
        return entry

    def supersede(
        self, project_id: UUID, old_id: UUID, new_published: PublishedKnowledge
    ) -> PublishedKnowledge:
        old_entry = self.repository.get_published(project_id, old_id)
        if not old_entry:
            raise KnowledgeReviewException("Old published knowledge not found.")

        old_superseded = old_entry.model_copy(
            update={
                "status": PublishedKnowledgeStatus.SUPERSEDED,
                "superseded_by_id": new_published.id,
            }
        )
        self.repository.save_published(old_superseded)

        new_entry = new_published.model_copy(update={"supersedes_id": old_entry.id})
        self.repository.save_published(new_entry)
        return new_entry

    def deprecate(
        self, project_id: UUID, entry_id: UUID, _reason: str, _actor: KnowledgeActor
    ) -> PublishedKnowledge:
        entry = self.repository.get_published(project_id, entry_id)
        if not entry:
            raise KnowledgeReviewException("Published knowledge not found.")
        deprecated = entry.model_copy(
            update={"status": PublishedKnowledgeStatus.DEPRECATED}
        )
        self.repository.save_published(deprecated)
        return deprecated


class KnowledgeApprovalService:
    def __init__(
        self, repository: KnowledgeRepository, lifecycle: KnowledgeLifecycleService
    ) -> None:
        self.repository, self.lifecycle = repository, lifecycle

    def approve_and_publish(
        self,
        project_id: UUID,
        candidate_id: UUID,
        actor: KnowledgeActor,
        comment: str | None = None,
    ) -> PublishedKnowledge:
        if actor.actor_type != KnowledgeActorType.HUMAN:
            raise KnowledgeReviewException("Only a human actor may approve knowledge.")
        candidate = self.repository.get_candidate(project_id, candidate_id)
        if not candidate or not candidate.is_pending():
            raise KnowledgeReviewException("Candidate is not pending review.")
        candidate.status, candidate.reviewed_by, candidate.review_comment = (
            KnowledgeCandidateStatus.APPROVED,
            actor,
            comment,
        )
        self.repository.save_candidate(candidate)
        return self.lifecycle.publish_from_candidate(candidate, actor)

    def reject(
        self,
        project_id: UUID,
        candidate_id: UUID,
        actor: KnowledgeActor,
        comment: str | None = None,
    ) -> KnowledgeCandidate:
        if actor.actor_type != KnowledgeActorType.HUMAN:
            raise KnowledgeReviewException("Only a human actor may review knowledge.")
        candidate = self.repository.get_candidate(project_id, candidate_id)
        if not candidate or not candidate.is_pending():
            raise KnowledgeReviewException("Candidate is not pending review.")
        candidate.status, candidate.reviewed_by, candidate.review_comment = (
            KnowledgeCandidateStatus.REJECTED,
            actor,
            comment,
        )
        self.repository.save_candidate(candidate)
        return candidate


class KnowledgeRetrievalService:
    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    def retrieve(self, query: KnowledgeRetrievalQuery) -> EngineeringKnowledgeContext:
        if not query.project_id or not query.stage:
            return EngineeringKnowledgeContext()
        profile = STAGE_PROFILES.get(query.stage)
        if not profile:
            return EngineeringKnowledgeContext()
        categories = set(query.categories or profile.default_categories)
        tags = set(query.tags or profile.default_tags)
        entries = [
            entry
            for entry in self.repository.list_published(
                query.project_id, PublishedKnowledgeStatus.ACTIVE
            )
            if entry.category in categories
            and (not tags or tags.intersection(entry.tags))
        ]
        entries.sort(key=lambda entry: (-entry.published_at.timestamp(), str(entry.id)))
        entries = entries[: min(query.max_entries, profile.max_entries)]
        section = (
            "## Engineering Knowledge\nNone\n"
            if not entries
            else "## Engineering Knowledge\n\n"
            + "\n\n".join(f"### {entry.title}\n{entry.content}" for entry in entries)
            + "\n"
        )
        return EngineeringKnowledgeContext(
            entry_ids=[entry.id for entry in entries],
            serialized_section=section,
            scope=KnowledgeScope.PROJECT,
        )

    def retrieve_for_stage(
        self, project_id: UUID, stage: WorkflowStage
    ) -> EngineeringKnowledgeContext:
        return self.retrieve(
            KnowledgeRetrievalQuery(project_id=project_id, stage=stage)
        )
