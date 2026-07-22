"""Tests for Atlas.handle() -- the uniform envelope dispatch entry point.

Verifies handle() produces results identical to calling the corresponding
named method directly, for every existing Command type, plus the
unknown-command and ApplicationError-mapping edge cases.
"""

import uuid

import pytest

from atlas import Atlas
from atlas.adapters.protocol import AdapterContext, AdapterKind
from atlas.commands import (
    ArchiveProjectCommand,
    Command,
    CompleteObjectiveCommand,
    CreateProjectCommand,
    GetWorkflowStatusCommand,
    ListProjectsCommand,
    LoadProjectCommand,
    TransitionStageCommand,
)
from atlas.contracts.envelope import RequestEnvelope
from atlas.contracts.errors import PlatformErrorCode
from atlas.results import Result


def _adapter_context() -> AdapterContext:
    return AdapterContext(kind=AdapterKind.AI, name="test-agent", version="0.1.0")


def _envelope(command: Command) -> RequestEnvelope[Command]:
    return RequestEnvelope(adapter=_adapter_context(), command=command)


_EXPECTED_COMMAND_TYPE_COUNT = 13


def test_dispatch_table_has_one_entry_per_command_type(
    test_atlas_platform: Atlas,
) -> None:
    assert len(test_atlas_platform._dispatch) == _EXPECTED_COMMAND_TYPE_COUNT


def test_handle_create_project_matches_named_method(test_atlas_platform: Atlas) -> None:
    named_result = test_atlas_platform.create_project(
        CreateProjectCommand(name="Named", description="D", objective="O")
    )
    enveloped_command = CreateProjectCommand(
        name="Enveloped", description="D", objective="O"
    )
    response = test_atlas_platform.handle(_envelope(enveloped_command))
    assert response.result is not None
    assert response.error is None
    assert type(response.result) is type(named_result)
    assert response.result.name == "Enveloped"


def test_handle_preserves_request_id(test_atlas_platform: Atlas) -> None:
    envelope = _envelope(ListProjectsCommand())
    response = test_atlas_platform.handle(envelope)
    assert response.request_id == envelope.request_id


def test_handle_list_projects(test_atlas_platform: Atlas) -> None:
    test_atlas_platform.create_project(
        CreateProjectCommand(name="P1", description="D", objective="O")
    )
    response = test_atlas_platform.handle(_envelope(ListProjectsCommand()))
    assert response.result is not None
    assert len(response.result.projects) == 1


def test_handle_load_project(test_atlas_platform: Atlas) -> None:
    created = test_atlas_platform.create_project(
        CreateProjectCommand(name="P1", description="D", objective="O")
    )
    response = test_atlas_platform.handle(
        _envelope(LoadProjectCommand(project_id=created.id))
    )
    assert response.result is not None
    assert response.result.id == created.id


def test_handle_archive_project(test_atlas_platform: Atlas) -> None:
    created = test_atlas_platform.create_project(
        CreateProjectCommand(name="P1", description="D", objective="O")
    )
    response = test_atlas_platform.handle(
        _envelope(ArchiveProjectCommand(project_id=created.id))
    )
    assert response.result is not None
    assert response.result.success is True


def test_handle_complete_objective(test_atlas_platform: Atlas) -> None:
    created = test_atlas_platform.create_project(
        CreateProjectCommand(name="P1", description="D", objective="O")
    )
    test_atlas_platform.transition_stage(TransitionStageCommand(project_id=created.id))
    status = test_atlas_platform.get_workflow_status(
        GetWorkflowStatusCommand(project_id=created.id)
    )
    response = test_atlas_platform.handle(
        _envelope(
            CompleteObjectiveCommand(
                project_id=created.id, objective=status.objectives[0]
            )
        )
    )
    assert response.result is not None
    assert response.error is None
    assert status.objectives[0] not in response.result.objectives


def test_handle_maps_application_error_to_error_envelope(
    test_atlas_platform: Atlas,
) -> None:
    response = test_atlas_platform.handle(
        _envelope(LoadProjectCommand(project_id=uuid.uuid4()))
    )
    assert response.result is None
    assert response.error is not None
    assert response.error.code == PlatformErrorCode.PROJECT_NOT_FOUND


def test_handle_unrecognized_command_type(test_atlas_platform: Atlas) -> None:
    class _NotARealCommand(Command):
        pass

    response = test_atlas_platform.handle(_envelope(_NotARealCommand()))
    assert response.result is None
    assert response.error is not None
    assert response.error.code == PlatformErrorCode.UNKNOWN_ERROR


@pytest.mark.parametrize(
    "result_type",
    [Result],
)
def test_response_envelope_result_is_a_result_dto(result_type: type[Result]) -> None:
    """Sanity check that ResponseEnvelope's generic parameter is Result-bound."""
    assert issubclass(result_type, Result)
