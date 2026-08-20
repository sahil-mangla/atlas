"""Tests for step scoring logic."""

from datetime import UTC, datetime
from uuid import uuid4

from atlas.adapters.protocol import AdapterKind
from atlas.capabilities.base import CapabilityName
from atlas.contracts.envelope import ResponseEnvelope
from atlas.contracts.errors import ErrorEnvelope, PlatformErrorCode
from atlas.observability.models import TraceOutcome, TraceRecord
from atlas.results import OperationResult, ProjectListResult
from evals.schema import CheckSpec, StepExpected
from evals.scoring import score_step


def _trace(**overrides: object) -> TraceRecord:
    defaults: dict[str, object] = {
        "request_id": uuid4(),
        "timestamp": datetime.now(UTC),
        "adapter": AdapterKind.AI,
        "capability": CapabilityName.PROJECT,
        "latency_ms": 1.0,
        "outcome": TraceOutcome.SUCCESS,
    }
    defaults.update(overrides)
    return TraceRecord(**defaults)  # type: ignore[arg-type]


def test_outcome_mismatch_short_circuits() -> None:
    expected = StepExpected(outcome="success", capability="project")
    failures = score_step(expected, "error", None, None, {})
    assert len(failures) == 1
    assert "outcome" in failures[0]


def test_capability_mismatch_fails() -> None:
    expected = StepExpected(outcome="success", capability="workflow")
    response = ResponseEnvelope(
        request_id=uuid4(), result=OperationResult(success=True)
    )
    trace = _trace(capability=CapabilityName.PROJECT)
    failures = score_step(expected, "success", response, trace, {})
    assert any("capability" in f for f in failures)


def test_capability_omitted_is_not_checked() -> None:
    expected = StepExpected(outcome="success")
    response = ResponseEnvelope(
        request_id=uuid4(), result=OperationResult(success=True)
    )
    trace = _trace(capability=CapabilityName.WORKFLOW)
    assert score_step(expected, "success", response, trace, {}) == []


def test_ai_provider_non_null_requires_a_provider() -> None:
    expected = StepExpected(outcome="success", ai_provider="non_null")
    trace = _trace(ai_provider=None)
    response = ResponseEnvelope(
        request_id=uuid4(), result=OperationResult(success=True)
    )
    failures = score_step(expected, "success", response, trace, {})
    assert any("ai_provider" in f for f in failures)


def test_error_code_match() -> None:
    expected = StepExpected(outcome="error", error_code="PROJECT_NOT_FOUND")
    error = ErrorEnvelope(code=PlatformErrorCode.PROJECT_NOT_FOUND, message="x")
    response: ResponseEnvelope[OperationResult] = ResponseEnvelope(
        request_id=uuid4(), error=error
    )
    assert score_step(expected, "error", response, None, {}) == []


def test_result_type_mismatch_fails() -> None:
    expected = StepExpected(outcome="success", result_type="ProjectListResult")
    response = ResponseEnvelope(
        request_id=uuid4(), result=OperationResult(success=True)
    )
    failures = score_step(expected, "success", response, None, {})
    assert any("result_type" in f for f in failures)


def test_check_equals_pass_and_fail() -> None:
    expected_ok = StepExpected(
        outcome="success", checks=[CheckSpec(field="result.projects", equals=[])]
    )
    expected_bad = StepExpected(
        outcome="success", checks=[CheckSpec(field="result.projects", equals=["x"])]
    )
    response = ResponseEnvelope(
        request_id=uuid4(), result=ProjectListResult(projects=[])
    )
    assert score_step(expected_ok, "success", response, None, {}) == []
    assert score_step(expected_bad, "success", response, None, {}) != []


def test_check_non_empty() -> None:
    expected = StepExpected(
        outcome="success",
        checks=[CheckSpec(field="result.projects", non_empty=True)],
    )
    response = ResponseEnvelope(
        request_id=uuid4(), result=ProjectListResult(projects=[])
    )
    failures = score_step(expected, "success", response, None, {})
    assert any("non-empty" in f for f in failures)


def test_check_equals_with_dollar_reference_substitution() -> None:
    request_id = uuid4()
    expected = StepExpected(
        outcome="success",
        checks=[CheckSpec(field="response.request_id", equals="$request_id")],
    )
    response = ResponseEnvelope(
        request_id=request_id, result=OperationResult(success=True)
    )
    failures = score_step(
        expected, "success", response, None, {"request_id": request_id}
    )
    assert failures == []
