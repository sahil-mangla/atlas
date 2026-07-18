# ruff: noqa: E501
from unittest.mock import ANY, Mock
from uuid import uuid4

from engine.domain.enums import KnowledgeSourceType
from engine.domain.knowledge import PublishedKnowledge
from engine.knowledge.orchestration import KnowledgeOrchestrationService


def test_orchestration_delegation() -> None:
    candidates = Mock()
    approval = Mock()
    retrieval = Mock()
    lifecycle = Mock()
    extractors = Mock()

    orchestration = KnowledgeOrchestrationService(
        candidates, approval, retrieval, lifecycle, extractors
    )

    # test extract
    extractors.extract.return_value = ["c1"]
    orchestration.extract_candidate_from_artifact(uuid4(), KnowledgeSourceType.RESEARCH_SNAPSHOT, uuid4())
    candidates.create.assert_called_with("c1")

    # test supersede
    mock_pub = Mock(spec=PublishedKnowledge)
    orchestration.supersede_knowledge(uuid4(), uuid4(), mock_pub)
    lifecycle.supersede.assert_called_with(ANY, ANY, mock_pub)
