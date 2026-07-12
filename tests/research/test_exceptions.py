from engine.research.exceptions import (
    InvalidResearchOperationException,
    ResearchException,
    ResearchNotFoundException,
)


def test_research_exceptions_inheritance() -> None:
    assert issubclass(ResearchException, Exception)
    assert issubclass(ResearchNotFoundException, ResearchException)
    assert issubclass(InvalidResearchOperationException, ResearchException)


def test_research_exceptions_instantiation() -> None:
    exc = ResearchNotFoundException("Not found")
    assert str(exc) == "Not found"
