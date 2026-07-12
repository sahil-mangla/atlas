from uuid import UUID, uuid4

from engine.domain.engineering_specification import EngineeringSpecification


def test_engineering_specification_defaults() -> None:
    spec = EngineeringSpecification(
        title="Init Core Domain",
        objective="Implement domain models",
    )
    assert isinstance(spec.id, UUID)
    assert spec.task_id is None
    assert spec.title == "Init Core Domain"
    assert spec.objective == "Implement domain models"
    assert spec.scope == ""
    assert spec.references == []
    assert spec.constraints == []
    assert spec.acceptance_criteria == []


def test_engineering_specification_custom() -> None:
    spec_id = uuid4()
    task_id = uuid4()

    spec = EngineeringSpecification(
        id=spec_id,
        task_id=task_id,
        title="Custom Spec",
        objective="Custom Objective",
        scope="engine/domain/",
        references=["Blueprint 10"],
        constraints=["Pydantic V2 only"],
        acceptance_criteria=["100% test coverage"],
    )

    assert spec.id == spec_id
    assert spec.task_id == task_id
    assert spec.title == "Custom Spec"
    assert spec.objective == "Custom Objective"
    assert spec.scope == "engine/domain/"
    assert spec.references == ["Blueprint 10"]
    assert spec.constraints == ["Pydantic V2 only"]
    assert spec.acceptance_criteria == ["100% test coverage"]
