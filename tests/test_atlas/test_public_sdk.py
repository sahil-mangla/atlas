"""Contract tests for the distributed Atlas SDK surface."""

from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

from pytest import MonkeyPatch

import atlas._bootstrap as bootstrap
from atlas import Atlas, create
from atlas.commands import CreateProjectCommand
from atlas.results import ProjectResult
from atlas.types import ProjectStatus
from engine.config import Settings


def test_public_factory_constructs_platform() -> None:
    platform = create()
    assert isinstance(platform, Atlas)


def test_bootstrap_injects_executor_into_ai_orchestration(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    executor = object()
    captured_executors: list[object] = []

    class RecordingOrchestrator:
        def __init__(
            self,
            received_executor: object,
            received_registry: object,
        ) -> None:
            self.prompt_executor = received_executor
            self.prompt_registry = received_registry
            captured_executors.append(received_executor)

    executor_constructor = Mock(return_value=executor)
    settings = Settings(workspace_root=tmp_path)
    monkeypatch.setattr(bootstrap, "get_settings", lambda: settings)
    monkeypatch.setattr(bootstrap, "PromptExecutor", executor_constructor)
    monkeypatch.setattr(bootstrap, "AIOrchestrationService", RecordingOrchestrator)

    platform = bootstrap._create_platform()

    assert isinstance(platform, Atlas)
    executor_constructor.assert_called_once()
    assert captured_executors == [executor]


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
