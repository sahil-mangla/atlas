from engine.planning.exceptions import (
    InvalidPlanningOperationException,
    PlanningException,
    PlanningNotFoundException,
)


def test_planning_exceptions_inheritance() -> None:
    assert issubclass(PlanningException, Exception)
    assert issubclass(PlanningNotFoundException, PlanningException)
    assert issubclass(InvalidPlanningOperationException, PlanningException)


def test_planning_exceptions_instantiation() -> None:
    exc = PlanningNotFoundException("Not found")
    assert str(exc) == "Not found"
