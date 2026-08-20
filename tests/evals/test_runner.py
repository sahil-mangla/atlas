"""Runner tests against the tiny 2-task fixture suite.

Uses MockAIProvider -- fast and deterministic, per the Step 3 spec's own
requirement for the runner's unit tests. This is distinct from the real
eval demonstration run, which uses only a live Ollama model (see
evals/__main__.py) and is not exercised in this suite.
"""

from pathlib import Path

from evals.loader import load_tasks
from evals.platform import build_eval_platform
from evals.report import (
    build_report,
    to_json_dict,
    to_markdown,
    write_json,
    write_markdown,
)
from evals.runner import run_task
from tests.ai.test_adapters import MockAIProvider

_FIXTURE = Path(__file__).parent / "fixtures" / "tiny.yaml"


def test_fixture_suite_runs_and_all_tasks_pass(tmp_path: Path) -> None:
    tasks = load_tasks(_FIXTURE)
    provider = MockAIProvider(stubbed_response="{}")
    platform, exporter = build_eval_platform(tmp_path, provider)

    results = [run_task(platform, task, exporter, provider) for task in tasks]

    assert len(results) == 2
    for result in results:
        assert result.passed, result.failures


def test_no_ai_task_has_null_trace_fields(tmp_path: Path) -> None:
    tasks = load_tasks(_FIXTURE)
    provider = MockAIProvider(stubbed_response="{}")
    platform, exporter = build_eval_platform(tmp_path, provider)

    result = run_task(platform, tasks[0], exporter, provider)

    assert result.trace_records[0].ai_provider is None
    assert result.trace_records[0].cost_usd is None


def test_report_structure_from_fixture_run(tmp_path: Path) -> None:
    tasks = load_tasks(_FIXTURE)
    provider = MockAIProvider(stubbed_response="{}")
    platform, exporter = build_eval_platform(tmp_path, provider)
    results = [run_task(platform, task, exporter, provider) for task in tasks]

    report = build_report("test-run", "MOCK:test", results)

    assert report.total_tasks == 2
    assert report.passed_tasks == 2
    assert report.pass_rate == 1.0
    assert report.pass_rate_by_adapter == {"cli": 1.0, "mcp": 1.0}
    assert report.pass_rate_by_category == {
        "tool_selection": 1.0,
        "error_handling": 1.0,
    }
    assert report.total_cost_usd is None

    json_dict = to_json_dict(report)
    assert json_dict["total_tasks"] == 2
    assert len(json_dict["task_results"]) == 2  # type: ignore[arg-type]

    markdown = to_markdown(report)
    assert "fixture-001-create-project" in markdown
    assert "PASS" in markdown


def test_report_writes_json_and_markdown_files(tmp_path: Path) -> None:
    tasks = load_tasks(_FIXTURE)
    provider = MockAIProvider(stubbed_response="{}")
    platform, exporter = build_eval_platform(tmp_path / "platform", provider)
    results = [run_task(platform, task, exporter, provider) for task in tasks]
    report = build_report("test-run", "MOCK:test", results)

    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"
    write_json(report, json_path)
    write_markdown(report, md_path)

    assert json_path.exists()
    assert md_path.exists()
    assert "fixture-002-load-nonexistent-project" in md_path.read_text(encoding="utf-8")


def test_failing_task_is_reported_as_failed(tmp_path: Path) -> None:
    """A task whose expectation doesn't match reality must fail, not pass
    silently -- guards against the scoring logic always returning true."""
    from evals.schema import (  # noqa: PLC0415
        CommandSpec,
        InputSpec,
        StepExpected,
        TaskSpec,
    )

    task = TaskSpec(
        task_id="deliberately-wrong",
        description="d",
        adapter="cli",
        category="tool_selection",
        input=InputSpec(command=CommandSpec(type="ListProjectsCommand", fields={})),
        expected=StepExpected(outcome="error"),  # ListProjectsCommand never errors
    )
    provider = MockAIProvider(stubbed_response="{}")
    platform, exporter = build_eval_platform(tmp_path, provider)

    result = run_task(platform, task, exporter, provider)

    assert result.passed is False
    assert result.failures
