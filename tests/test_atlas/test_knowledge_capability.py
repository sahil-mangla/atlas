"""Unit tests for KnowledgeCapability's internal exception mapping.

Sprint 1 (Phase 16 Platform Hardening) audit finding: review_knowledge_candidate
previously caught (WorkflowException, KnowledgeException) and re-raised the bare
ApplicationError base class, which has no entry in _ERROR_CODE_MAP -- every
knowledge-review failure surfaced over Atlas.handle() as UNKNOWN_ERROR, the code
PlatformErrorCode reserves for a programming defect, not routine application
behavior. This mirrors the per-subclass mapping every other capability already
does and closes the gap with a dedicated KnowledgeReviewError/error code.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from atlas.capabilities.knowledge_capability import KnowledgeCapability
from atlas.commands import ListKnowledgeCandidatesCommand, ShowKnowledgeCandidateCommand
from atlas.contracts.errors import PlatformErrorCode, to_error_envelope
from atlas.exceptions import (
    ApplicationError,
    InvalidTransitionError,
    KnowledgeReviewError,
    WorkflowNotReadyError,
)
from engine.knowledge.exceptions import (
    InvalidKnowledgeException,
    KnowledgeException,
    KnowledgeReviewException,
)
from engine.workflow.exceptions import (
    InvalidTransitionException,
    WorkflowException,
    WorkflowNotFoundException,
)


def _capability() -> KnowledgeCapability:
    return KnowledgeCapability(orchestration_service=MagicMock())


def _capability_with_orchestration(
    knowledge_orchestration: MagicMock,
) -> KnowledgeCapability:
    orchestration_service = MagicMock()
    orchestration_service.knowledge_orchestration = knowledge_orchestration
    return KnowledgeCapability(orchestration_service=orchestration_service)


def test_map_workflow_exception_maps_not_found() -> None:
    capability = _capability()
    result = capability._map_workflow_exception(WorkflowNotFoundException("x"))
    assert isinstance(result, WorkflowNotReadyError)


def test_map_workflow_exception_maps_invalid_transition() -> None:
    capability = _capability()
    result = capability._map_workflow_exception(InvalidTransitionException("x"))
    assert isinstance(result, InvalidTransitionError)


def test_map_workflow_exception_maps_generic_workflow_exception() -> None:
    capability = _capability()
    result = capability._map_workflow_exception(WorkflowException("x"))
    assert type(result) is ApplicationError


def test_map_knowledge_exception_maps_invalid_knowledge() -> None:
    capability = _capability()
    result = capability._map_knowledge_exception(InvalidKnowledgeException("x"))
    assert isinstance(result, KnowledgeReviewError)


def test_map_knowledge_exception_maps_review_violation() -> None:
    capability = _capability()
    result = capability._map_knowledge_exception(KnowledgeReviewException("x"))
    assert isinstance(result, KnowledgeReviewError)


def test_knowledge_review_error_is_not_unknown_error_on_the_wire() -> None:
    """Regression test: knowledge-review failures must not surface as UNKNOWN_ERROR."""
    capability = _capability()
    mapped = capability._map_knowledge_exception(KnowledgeException("boom"))
    envelope = to_error_envelope(mapped)
    assert envelope.code == PlatformErrorCode.KNOWLEDGE_REVIEW_ERROR


def test_list_candidates_maps_knowledge_exception() -> None:
    """A corrupt on-disk candidate file must surface as KnowledgeReviewError
    through Atlas.handle(), not an unhandled KnowledgeException -- handle()
    only catches ApplicationError."""
    knowledge_orchestration = MagicMock()
    knowledge_orchestration.list_candidates.side_effect = InvalidKnowledgeException(
        "corrupt"
    )
    capability = _capability_with_orchestration(knowledge_orchestration)

    with pytest.raises(KnowledgeReviewError):
        capability.list_candidates(ListKnowledgeCandidatesCommand(project_id=uuid4()))


def test_show_candidate_maps_knowledge_exception() -> None:
    knowledge_orchestration = MagicMock()
    knowledge_orchestration.get_candidate.side_effect = InvalidKnowledgeException(
        "corrupt"
    )
    capability = _capability_with_orchestration(knowledge_orchestration)

    with pytest.raises(KnowledgeReviewError):
        capability.show_candidate(
            ShowKnowledgeCandidateCommand(project_id=uuid4(), candidate_id=uuid4())
        )
