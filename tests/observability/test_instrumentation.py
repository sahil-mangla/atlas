"""Tests for the wired-together instrumentation layer, exercised through
``Atlas.handle()`` -- the actual envelope-boundary chokepoint."""

import uuid
from pathlib import Path

import pytest

from atlas import Atlas
from atlas._service import _COMMAND_CAPABILITY
from atlas.adapters.protocol import AdapterContext, AdapterKind
from atlas.capabilities.base import CapabilityName
from atlas.commands import (
    Command,
    CreateProjectCommand,
    ExecuteStageCommand,
    LoadProjectCommand,
    TransitionStageCommand,
)
from atlas.contracts.envelope import RequestEnvelope
from atlas.contracts.errors import PlatformErrorCode
from atlas.observability.exporter import TraceExporter
from atlas.observability.instrumentation import instrument_request
from atlas.observability.models import TraceOutcome, TraceRecord
from atlas.types import WorkflowStage
from engine.domain.ai_drafts import ResearchProposalDraft
from tests.ai.test_adapters import MockAIProvider
from tests.support.test_bootstrap import create_test_platform


class ListExporter:
    """In-memory TraceExporter test double."""

    def __init__(self) -> None:
        self.records: list[TraceRecord] = []

    def export(self, record: TraceRecord) -> None:
        self.records.append(record)


def _envelope(command: Command) -> RequestEnvelope[Command]:
    return RequestEnvelope(
        adapter=AdapterContext(kind=AdapterKind.AI, name="test-agent", version="0.1.0"),
        command=command,
    )


def _platform(tmp_path: Path, exporter: TraceExporter, **kwargs: object) -> Atlas:
    return create_test_platform(tmp_path, exporter=exporter, **kwargs)  # type: ignore[arg-type]


def test_command_capability_table_matches_dispatch_table(tmp_path: Path) -> None:
    platform = create_test_platform(tmp_path)
    assert set(_COMMAND_CAPABILITY) == set(platform._dispatch)


def test_no_ai_command_produces_a_record_with_null_ai_fields(tmp_path: Path) -> None:
    exporter = ListExporter()
    platform = _platform(tmp_path, exporter)

    platform.handle(
        _envelope(CreateProjectCommand(name="P", description="D", objective="O"))
    )

    assert len(exporter.records) == 1
    record = exporter.records[0]
    assert record.capability == CapabilityName.PROJECT
    assert record.ai_provider is None
    assert record.prompt_tokens is None
    assert record.completion_tokens is None
    assert record.total_tokens is None
    assert record.cost_usd is None
    assert record.outcome == TraceOutcome.SUCCESS
    assert record.adapter == AdapterKind.AI


def test_ai_command_produces_a_record_with_populated_token_fields(
    tmp_path: Path,
) -> None:
    provider = MockAIProvider(stubbed_response="{}")
    exporter = ListExporter()
    platform = _platform(tmp_path, exporter, ai_provider=provider)

    proj = platform.create_project(
        CreateProjectCommand(name="P", description="D", objective="O")
    )
    platform.transition_stage(TransitionStageCommand(project_id=proj.id))
    draft = ResearchProposalDraft(problem_statement="P", objectives=["O"])
    provider.stubbed_response = draft.model_dump_json()
    # create_project/transition_stage above dispatch via named methods, not
    # handle() -- confirmed by test_named_method_calls_never_export_a_record
    # to never export a record, so no records exist yet at this point.

    platform.handle(
        _envelope(ExecuteStageCommand(project_id=proj.id, stage=WorkflowStage.RESEARCH))
    )

    assert len(exporter.records) == 1
    record = exporter.records[0]
    assert record.capability == CapabilityName.WORKFLOW_EXECUTION
    assert record.ai_provider == "mockaiprovider"
    assert record.prompt_tokens == 10
    assert record.completion_tokens == 0
    assert record.total_tokens == 10
    assert record.outcome == TraceOutcome.SUCCESS


def test_error_command_produces_a_record_with_error_outcome(tmp_path: Path) -> None:
    exporter = ListExporter()
    platform = _platform(tmp_path, exporter)

    platform.handle(_envelope(LoadProjectCommand(project_id=uuid.uuid4())))

    assert len(exporter.records) == 1
    record = exporter.records[0]
    assert record.outcome == TraceOutcome.ERROR
    assert record.error_code == PlatformErrorCode.PROJECT_NOT_FOUND
    assert record.cost_usd is None


def test_unexpected_dispatch_exception_is_traced_and_reraised() -> None:
    exporter = ListExporter()
    envelope = _envelope(CreateProjectCommand(name="P", description="D", objective="O"))
    error = RuntimeError("dispatch exploded")

    def dispatch(_envelope: RequestEnvelope[Command]) -> object:
        raise error

    with pytest.raises(RuntimeError, match="dispatch exploded") as raised:
        instrument_request(
            envelope, dispatch, lambda _command: CapabilityName.PROJECT, exporter
        )

    assert raised.value is error
    assert len(exporter.records) == 1
    record = exporter.records[0]
    assert record.request_id == envelope.request_id
    assert record.capability == CapabilityName.PROJECT
    assert record.outcome == TraceOutcome.ERROR
    assert record.error_code is None


def test_unrecognized_command_produces_a_record_with_null_capability(
    tmp_path: Path,
) -> None:
    class _NotARealCommand(Command):
        pass

    exporter = ListExporter()
    platform = _platform(tmp_path, exporter)

    platform.handle(_envelope(_NotARealCommand()))

    assert len(exporter.records) == 1
    record = exporter.records[0]
    assert record.capability is None
    assert record.outcome == TraceOutcome.ERROR
    assert record.error_code == PlatformErrorCode.UNKNOWN_ERROR


def test_instrumentation_disabled_produces_no_exporter_calls(tmp_path: Path) -> None:
    exporter = ListExporter()
    platform = _platform(tmp_path, exporter, instrumentation_enabled=False)

    platform.handle(
        _envelope(CreateProjectCommand(name="P", description="D", objective="O"))
    )

    assert exporter.records == []


def test_direct_construction_defaults_to_null_exporter_with_no_side_effects(
    tmp_path: Path,
) -> None:
    """Constructing Atlas without an explicit exporter must not touch the
    filesystem -- this is the fix for the bootstrap-wiring bug where an
    implicit get_settings() call would have written into a guessed path
    instead of tmp_path during every test run."""
    platform = create_test_platform(tmp_path)

    platform.handle(
        _envelope(CreateProjectCommand(name="P", description="D", objective="O"))
    )

    assert list(tmp_path.iterdir()) == [tmp_path / "workspace"]


def test_dispatch_and_handle_results_are_unaffected_by_instrumentation(
    tmp_path: Path,
) -> None:
    """handle()'s observable result shape must be identical whether or not
    instrumentation is on -- mirrors tests/test_atlas/test_platform_handle.py."""
    exporter = ListExporter()
    platform = _platform(tmp_path, exporter)

    response = platform.handle(
        _envelope(
            CreateProjectCommand(name="Enveloped", description="D", objective="O")
        )
    )

    assert response.result is not None
    assert response.error is None
    assert response.result.name == "Enveloped"


@pytest.mark.parametrize("instrumentation_enabled", [True, False])
def test_named_method_calls_never_export_a_record(
    tmp_path: Path, instrumentation_enabled: bool
) -> None:
    """Named-method dispatch (what CLI actually uses today) bypasses
    handle() entirely, so it must never produce a trace record."""
    exporter = ListExporter()
    platform = _platform(
        tmp_path, exporter, instrumentation_enabled=instrumentation_enabled
    )

    platform.create_project(
        CreateProjectCommand(name="P", description="D", objective="O")
    )

    assert exporter.records == []
