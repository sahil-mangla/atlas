# ruff: noqa: E501
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from engine.domain.ai_drafts import KnowledgeCandidateDraft
from engine.domain.enums import (
    KnowledgeActorType,
    KnowledgeCandidateStatus,
    KnowledgeCategory,
    KnowledgeSourceType,
    PublishedKnowledgeStatus,
    WorkflowStage,
)
from engine.domain.knowledge import (
    HumanKnowledgeSubmission,
    KnowledgeActor,
    KnowledgeCandidate,
    KnowledgeProvenance,
    KnowledgeRetrievalQuery,
    PublishedKnowledge,
)
from engine.knowledge.exceptions import KnowledgeReviewException
from engine.knowledge.services import (
    KnowledgeApprovalService,
    KnowledgeCandidateService,
    KnowledgeLifecycleService,
    KnowledgeRetrievalService,
)


def test_candidate_service_create_from_ai_draft() -> None:
    repo = Mock()
    dedup = Mock()
    dedup.check.return_value = Mock(is_exact_duplicate=False)

    svc = KnowledgeCandidateService(repo, dedup)
    draft = KnowledgeCandidateDraft(
        title="AI Draft",
        content="Content",
        category=KnowledgeCategory.PATTERN,
        tags=["ai"],
        rationale="Because",
        source_snapshot_type=KnowledgeSourceType.RESEARCH_SNAPSHOT,
        source_snapshot_id=uuid4(),
    )
    actor = KnowledgeActor(
        actor_type=KnowledgeActorType.SYSTEM, actor_id="sys", display_name="sys"
    )

    candidate = svc.create_from_ai_draft(uuid4(), draft, actor)
    assert candidate is not None
    assert candidate.title == "AI Draft"
    assert candidate.category == KnowledgeCategory.PATTERN
    assert repo.save_candidate.called


def test_candidate_service_create_from_submission() -> None:
    repo = Mock()
    dedup = Mock()
    dedup.check.return_value = Mock(
        is_exact_duplicate=False, normalized_fingerprint="fp1"
    )

    svc = KnowledgeCandidateService(repo, dedup)
    actor = KnowledgeActor(
        actor_type=KnowledgeActorType.HUMAN, actor_id="user1", display_name="User One"
    )
    sub = HumanKnowledgeSubmission(
        title="Human Submission",
        content="Interesting findings.",
        category=KnowledgeCategory.LESSON_LEARNED,
        tags=["lessons"],
        actor=actor,
    )
    candidate = svc.create_from_submission(uuid4(), sub)
    assert candidate is not None
    assert candidate.title == "Human Submission"
    assert candidate.category == KnowledgeCategory.LESSON_LEARNED
    assert candidate.author == actor
    assert repo.save_candidate.called


def test_candidate_service_withdraw() -> None:
    repo = Mock()
    dedup = Mock()
    svc = KnowledgeCandidateService(repo, dedup)

    project_id = uuid4()
    candidate_id = uuid4()
    actor = KnowledgeActor(actor_type=KnowledgeActorType.HUMAN, actor_id="user1")

    # 1. Successful withdraw
    pending_candidate = KnowledgeCandidate(
        id=candidate_id,
        project_id=project_id,
        title="Test",
        content="Content",
        category=KnowledgeCategory.CONSTRAINT,
        provenance=KnowledgeProvenance(
            source_type=KnowledgeSourceType.HUMAN_SUBMISSION,
            source_id=uuid4(),
            extracted_at=datetime.now(UTC),
            actor=actor,
        ),
        author=actor,
        status=KnowledgeCandidateStatus.PENDING_REVIEW,
        created_at=datetime.now(UTC),
    )
    repo.get_candidate.return_value = pending_candidate

    withdrawn = svc.withdraw(project_id, candidate_id, actor)
    assert withdrawn.status == KnowledgeCandidateStatus.WITHDRAWN
    assert withdrawn.reviewed_by == actor
    assert repo.save_candidate.called

    # 2. Withdraw fails if status is not pending
    pending_candidate.status = KnowledgeCandidateStatus.APPROVED
    with pytest.raises(
        KnowledgeReviewException, match="Only pending candidates may be withdrawn"
    ):
        svc.withdraw(project_id, candidate_id, actor)


def test_approval_service_approve_and_publish() -> None:
    repo = Mock()
    lifecycle = Mock()
    svc = KnowledgeApprovalService(repo, lifecycle)

    project_id = uuid4()
    candidate_id = uuid4()
    human_actor = KnowledgeActor(actor_type=KnowledgeActorType.HUMAN, actor_id="user1")
    ai_actor = KnowledgeActor(actor_type=KnowledgeActorType.AI, actor_id="ai_bot")
    system_actor = KnowledgeActor(actor_type=KnowledgeActorType.SYSTEM, actor_id="sys")

    # 1. Non-human approves: raises exception
    with pytest.raises(
        KnowledgeReviewException, match="Only a human actor may approve"
    ):
        svc.approve_and_publish(project_id, candidate_id, ai_actor)

    with pytest.raises(
        KnowledgeReviewException, match="Only a human actor may approve"
    ):
        svc.approve_and_publish(project_id, candidate_id, system_actor)

    # 2. Candidate not pending review: raises exception
    repo.get_candidate.return_value = None
    with pytest.raises(
        KnowledgeReviewException, match="Candidate is not pending review"
    ):
        svc.approve_and_publish(project_id, candidate_id, human_actor)

    pending_candidate = KnowledgeCandidate(
        id=candidate_id,
        project_id=project_id,
        title="Valid Candidate",
        content="Content",
        category=KnowledgeCategory.CONSTRAINT,
        provenance=KnowledgeProvenance(
            source_type=KnowledgeSourceType.HUMAN_SUBMISSION,
            source_id=uuid4(),
            extracted_at=datetime.now(UTC),
            actor=human_actor,
        ),
        author=human_actor,
        status=KnowledgeCandidateStatus.PENDING_REVIEW,
        created_at=datetime.now(UTC),
    )
    repo.get_candidate.return_value = pending_candidate

    # 3. Successful approval
    published_mock = Mock(spec=PublishedKnowledge)
    lifecycle.publish_from_candidate.return_value = published_mock

    res = svc.approve_and_publish(
        project_id, candidate_id, human_actor, comment="Approved indeed!"
    )
    assert pending_candidate.status == KnowledgeCandidateStatus.APPROVED
    assert pending_candidate.reviewed_by == human_actor
    assert pending_candidate.review_comment == "Approved indeed!"
    assert res == published_mock
    repo.save_candidate.assert_called_with(pending_candidate)
    lifecycle.publish_from_candidate.assert_called_once_with(
        pending_candidate, human_actor
    )


def test_approval_service_reject() -> None:
    repo = Mock()
    lifecycle = Mock()
    svc = KnowledgeApprovalService(repo, lifecycle)

    project_id = uuid4()
    candidate_id = uuid4()
    human_actor = KnowledgeActor(actor_type=KnowledgeActorType.HUMAN, actor_id="user1")
    ai_actor = KnowledgeActor(actor_type=KnowledgeActorType.AI, actor_id="ai_bot")

    # 1. Non-human rejects raises exception
    with pytest.raises(KnowledgeReviewException, match="Only a human actor may review"):
        svc.reject(project_id, candidate_id, ai_actor)

    pending_candidate = KnowledgeCandidate(
        id=candidate_id,
        project_id=project_id,
        title="To be rejected",
        content="Content",
        category=KnowledgeCategory.CONSTRAINT,
        provenance=KnowledgeProvenance(
            source_type=KnowledgeSourceType.HUMAN_SUBMISSION,
            source_id=uuid4(),
            extracted_at=datetime.now(UTC),
            actor=human_actor,
        ),
        author=human_actor,
        status=KnowledgeCandidateStatus.PENDING_REVIEW,
        created_at=datetime.now(UTC),
    )
    repo.get_candidate.return_value = pending_candidate

    # 2. Successful rejection
    res = svc.reject(
        project_id, candidate_id, human_actor, comment="Not standard compliance."
    )
    assert pending_candidate.status == KnowledgeCandidateStatus.REJECTED
    assert pending_candidate.reviewed_by == human_actor
    assert pending_candidate.review_comment == "Not standard compliance."
    assert res == pending_candidate
    repo.save_candidate.assert_called_with(pending_candidate)
    lifecycle.publish_from_candidate.assert_not_called()


def test_lifecycle_service_supersede_and_deprecate() -> None:
    repo = Mock()
    svc = KnowledgeLifecycleService(repo)

    project_id = uuid4()
    actor = KnowledgeActor(actor_type=KnowledgeActorType.HUMAN, actor_id="user")
    prov = KnowledgeProvenance(
        source_type=KnowledgeSourceType.HUMAN_SUBMISSION,
        source_id=uuid4(),
        extracted_at=datetime.now(UTC),
        actor=actor,
    )

    candidate = KnowledgeCandidate(
        id=uuid4(),
        project_id=project_id,
        title="Original Candidate",
        content="Original content.",
        category=KnowledgeCategory.PATTERN,
        provenance=prov,
        author=actor,
        status=KnowledgeCandidateStatus.APPROVED,
        created_at=datetime.now(UTC),
        deduplication_fingerprint="fp1",
    )

    # 1. publish_from_candidate
    published = svc.publish_from_candidate(candidate, actor)
    assert published.version == 1
    assert published.status == PublishedKnowledgeStatus.ACTIVE
    assert published.candidate_id == candidate.id
    assert published.title == candidate.title
    assert repo.save_published.call_count == 1

    # Reset mock call count
    repo.save_published.reset_mock()

    # 2. supersede
    repo.get_published.return_value = published

    new_published = PublishedKnowledge(
        id=uuid4(),
        project_id=project_id,
        title="Updated Title",
        content="Updated content.",
        category=KnowledgeCategory.PATTERN,
        provenance=prov,
        author=actor,
        published_at=datetime.now(UTC),
        version=2,
        candidate_id=uuid4(),
        deduplication_fingerprint="fp2",
    )

    superseded_entry = svc.supersede(project_id, published.id, new_published)
    # Check that save_published was called twice: once for updating old, once for new
    assert repo.save_published.call_count == 2

    # Check backlink updates
    # The superseded old one should have status SUPERSEDED and superseded_by_id pointing to new_published.id
    first_save = repo.save_published.call_args_list[0][0][0]
    assert first_save.status == PublishedKnowledgeStatus.SUPERSEDED
    assert first_save.superseded_by_id == new_published.id

    # The new one returned should have supersedes_id set to old published.id
    assert superseded_entry.supersedes_id == published.id

    # 3. deprecate
    repo.get_published.return_value = new_published
    repo.save_published.reset_mock()

    deprecated = svc.deprecate(project_id, new_published.id, "Stale rule", actor)
    assert deprecated.status == PublishedKnowledgeStatus.DEPRECATED
    repo.save_published.assert_called_once_with(deprecated)


def test_retrieval_service() -> None:
    repo = Mock()
    svc = KnowledgeRetrievalService(repo)

    project_id = uuid4()
    actor = KnowledgeActor(actor_type=KnowledgeActorType.HUMAN, actor_id="user")
    prov = KnowledgeProvenance(
        source_type=KnowledgeSourceType.HUMAN_SUBMISSION,
        source_id=uuid4(),
        extracted_at=datetime.now(UTC),
        actor=actor,
    )

    # Empty retrieval behavior
    repo.list_published.return_value = []
    empty_ctx = svc.retrieve_for_stage(project_id, WorkflowStage.RESEARCH)
    assert len(empty_ctx.entry_ids) == 0
    assert "None" in empty_ctx.serialized_section

    # Retrieval with content
    published_items = [
        PublishedKnowledge(
            id=uuid4(),
            project_id=project_id,
            title="Lesson 1",
            content="Do not leak secrets.",
            category=KnowledgeCategory.LESSON_LEARNED,
            tags=["security"],
            status=PublishedKnowledgeStatus.ACTIVE,
            provenance=prov,
            author=actor,
            published_at=datetime(2026, 7, 1, tzinfo=UTC),
            version=1,
            candidate_id=uuid4(),
            deduplication_fingerprint="fp1",
        ),
        PublishedKnowledge(
            id=uuid4(),
            project_id=project_id,
            title="Standard 1",
            content="Use double quotes.",
            category=KnowledgeCategory.STANDARD,
            tags=["style"],
            status=PublishedKnowledgeStatus.ACTIVE,
            provenance=prov,
            author=actor,
            published_at=datetime(2026, 7, 2, tzinfo=UTC),
            version=1,
            candidate_id=uuid4(),
            deduplication_fingerprint="fp2",
        ),
        PublishedKnowledge(
            id=uuid4(),
            project_id=project_id,
            title="Constraint 1",
            content="Single workspace root.",
            category=KnowledgeCategory.CONSTRAINT,
            tags=["workspace", "security"],
            status=PublishedKnowledgeStatus.ACTIVE,
            provenance=prov,
            author=actor,
            published_at=datetime(2026, 7, 3, tzinfo=UTC),
            version=1,
            candidate_id=uuid4(),
            deduplication_fingerprint="fp3",
        ),
    ]
    repo.list_published.return_value = published_items

    # Test Stage profiles: RESEARCH stage selects LESSON_LEARNED and CONSTRAINT categories by default
    # Constraint 1 (July 3) should come first, then Lesson 1 (July 1)
    res_ctx = svc.retrieve_for_stage(project_id, WorkflowStage.RESEARCH)
    assert len(res_ctx.entry_ids) == 2
    assert (
        res_ctx.entry_ids[0] == published_items[2].id
    )  # Constraint 1 (published_at July 3)
    assert (
        res_ctx.entry_ids[1] == published_items[0].id
    )  # Lesson 1 (published_at July 1)
    assert "Constraint 1" in res_ctx.serialized_section
    assert "Lesson 1" in res_ctx.serialized_section
    assert (
        "Standard 1" not in res_ctx.serialized_section
    )  # Category not matches RESEARCH profile defaults

    # Custom Query with Category and Tag filters
    query = KnowledgeRetrievalQuery(
        project_id=project_id,
        stage=WorkflowStage.RESEARCH,
        categories=[KnowledgeCategory.LESSON_LEARNED, KnowledgeCategory.STANDARD],
        tags=["style"],
        max_entries=5,
    )
    custom_ctx = svc.retrieve(query)
    # Only Standard 1 has category in [LESSON_LEARNED, STANDARD] AND tags intersecting ['style']
    assert len(custom_ctx.entry_ids) == 1
    assert custom_ctx.entry_ids[0] == published_items[1].id
    assert "Standard 1" in custom_ctx.serialized_section

    # Test max_entries limit
    query_limit = KnowledgeRetrievalQuery(
        project_id=project_id,
        stage=WorkflowStage.RESEARCH,
        categories=[KnowledgeCategory.LESSON_LEARNED, KnowledgeCategory.CONSTRAINT],
        max_entries=1,
    )
    limit_ctx = svc.retrieve(query_limit)
    assert len(limit_ctx.entry_ids) == 1
    assert limit_ctx.entry_ids[0] == published_items[2].id  # Constraint 1 comes first
