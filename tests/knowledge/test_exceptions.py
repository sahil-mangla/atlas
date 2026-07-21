from engine.knowledge.exceptions import (
    InvalidKnowledgeException,
    KnowledgeException,
    KnowledgeReviewException,
)


def test_exception_hierarchy() -> None:
    assert issubclass(InvalidKnowledgeException, KnowledgeException)
    assert issubclass(KnowledgeReviewException, KnowledgeException)
