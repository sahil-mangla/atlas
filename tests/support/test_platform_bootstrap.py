"""Bootstrap wiring tests for the Phase 14 presentation composition root.

Verifies the composition root (atlas/_bootstrap.py, mirrored here by
create_test_platform) explicitly constructs and wires collectors, the
renderer registry, and PlatformOrchestrationService onto the Atlas facade --
with constructor injection throughout and no service locator.
"""

from pathlib import Path

from atlas._service import Atlas
from presentation.collectors.collectors import (
    DiagnosticsCollector,
    KnowledgeSummaryCollector,
    ProjectDashboardCollector,
    ResearchSummaryCollector,
    WorkflowStatusCollector,
)
from presentation.orchestration import PlatformOrchestrationService
from presentation.renderers import RendererRegistry
from tests.support.test_bootstrap import create_test_platform


def test_bootstrap_attaches_platform_orchestration(tmp_path: Path) -> None:
    atlas = create_test_platform(tmp_path)
    assert atlas._platform_orchestration is not None
    assert isinstance(atlas._platform_orchestration, PlatformOrchestrationService)


def test_bootstrap_attaches_renderer_registry(tmp_path: Path) -> None:
    atlas = create_test_platform(tmp_path)
    assert atlas._renderer_registry is not None
    assert isinstance(atlas._renderer_registry, RendererRegistry)


def test_bootstrap_registers_all_three_renderers(tmp_path: Path) -> None:
    atlas = create_test_platform(tmp_path)
    registry = atlas._renderer_registry
    assert registry is not None
    for name in ("json", "markdown", "cli"):
        assert registry.resolve(name).name == name


def test_bootstrap_wires_collectors_via_constructor_injection(tmp_path: Path) -> None:
    """PlatformOrchestrationService never constructs its own collectors --
    the composition root does, and passes them in."""
    atlas = create_test_platform(tmp_path)
    orchestration = atlas._platform_orchestration
    assert orchestration is not None
    assert isinstance(orchestration.project_dashboard, ProjectDashboardCollector)
    assert isinstance(orchestration.workflow_status, WorkflowStatusCollector)
    assert isinstance(orchestration.research_summary, ResearchSummaryCollector)
    assert isinstance(orchestration.knowledge_summary, KnowledgeSummaryCollector)
    assert isinstance(orchestration.diagnostics, DiagnosticsCollector)


def test_platform_orchestration_service_does_not_construct_collectors_itself() -> None:
    """PlatformOrchestrationService.__init__ only assigns; it must not import
    or instantiate any Collector class."""
    import inspect

    source = inspect.getsource(PlatformOrchestrationService.__init__)
    for collector_name in (
        "ProjectDashboardCollector(",
        "WorkflowStatusCollector(",
        "ResearchSummaryCollector(",
        "KnowledgeSummaryCollector(",
        "DiagnosticsCollector(",
    ):
        assert collector_name not in source, (
            f"PlatformOrchestrationService must not construct {collector_name}"
        )


def test_production_bootstrap_module_wires_presentation() -> None:
    """Static check that atlas/_bootstrap.py (the real composition root, not
    just the test helper) performs the same wiring."""
    import inspect

    import atlas._bootstrap as bootstrap_module

    source = inspect.getsource(bootstrap_module)
    assert "PlatformOrchestrationService(" in source
    assert "RendererRegistry(" in source
    assert "_bind_presentation" in source
    assert "ProjectDashboardCollector(atlas)" in source


def test_atlas_class_has_no_service_locator() -> None:
    """Atlas resolves presentation dependencies through explicit attributes
    set once at construction/bind time, not through a runtime registry or
    locator pattern that presentation classes could pull from."""
    import inspect

    source = inspect.getsource(Atlas)
    assert "ServiceLocator" not in source
    assert "get_service(" not in source
    assert "container.resolve(" not in source
