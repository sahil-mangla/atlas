"""Contract tests for the distributed Atlas SDK surface."""

from uuid import uuid4

from atlas import Atlas, create
from atlas.commands import CreateProjectCommand
from atlas.results import ProjectResult
from atlas.types import ProjectStatus


def test_public_factory_constructs_platform() -> None:
    platform = create()
    assert isinstance(platform, Atlas)


def test_public_dto_serialization_is_stable() -> None:
    command = CreateProjectCommand(
        name="SDK",
        description="Public contract",
        objective="Verify serialization",
    )
    assert command.model_dump()["name"] == "SDK"

    result = ProjectResult(
        id=uuid4(),
        name=command.name,
        description=command.description,
        objective=command.objective,
        status=ProjectStatus.INITIALIZED,
    )
    assert result.model_dump()["status"] == ProjectStatus.INITIALIZED
