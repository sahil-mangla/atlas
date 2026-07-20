"""Static import-boundary guard for the Phase 15 platform layer.

Verifies the capability/contract/adapter dependency rules from
docs/plans/phase-15-platform-layer.md §3.2/§9.3:

    atlas/capabilities/* -> engine/* (only the repos/services Atlas already used)
    atlas/capabilities/* never imports another atlas/capabilities/* module
    atlas/contracts/* and atlas/adapters/* never import engine/* or presentation/*
    clients/* never imports atlas/capabilities/* (capabilities are Atlas-internal)
    clients/cli/application.py still never imports engine/*
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPABILITIES_ROOT = REPO_ROOT / "atlas" / "capabilities"
CONTRACTS_ROOT = REPO_ROOT / "atlas" / "contracts"
ADAPTERS_ROOT = REPO_ROOT / "atlas" / "adapters"
CLIENTS_ROOT = REPO_ROOT / "clients"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def _iter_py_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


@pytest.mark.parametrize(
    "path",
    _iter_py_files(CONTRACTS_ROOT),
    ids=lambda p: str(p.relative_to(CONTRACTS_ROOT)),
)
def test_contracts_module_has_no_engine_or_presentation_imports(path: Path) -> None:
    modules = _imported_modules(path)
    forbidden = {
        m
        for m in modules
        if m == "engine"
        or m.startswith("engine.")
        or m == "presentation"
        or m.startswith("presentation.")
    }
    assert not forbidden, f"{path} imports forbidden modules: {forbidden}"


@pytest.mark.parametrize(
    "path",
    _iter_py_files(ADAPTERS_ROOT),
    ids=lambda p: str(p.relative_to(ADAPTERS_ROOT)),
)
def test_adapters_module_has_no_engine_or_presentation_imports(path: Path) -> None:
    modules = _imported_modules(path)
    forbidden = {
        m
        for m in modules
        if m == "engine"
        or m.startswith("engine.")
        or m == "presentation"
        or m.startswith("presentation.")
    }
    assert not forbidden, f"{path} imports forbidden modules: {forbidden}"


@pytest.mark.parametrize(
    "path",
    [
        p
        for p in _iter_py_files(CAPABILITIES_ROOT)
        if p.name not in ("base.py", "__init__.py")
    ],
    ids=lambda p: str(p.relative_to(CAPABILITIES_ROOT)),
)
def test_capability_module_does_not_import_another_capability_module(
    path: Path,
) -> None:
    """No capability *implementation* module imports another capability's
    implementation module -- each may import atlas.capabilities.base (the
    shared CapabilityName enum) freely. The package's own __init__.py is
    exempt: it is the sole place expected to re-export all five classes
    (§3.6 of the Phase 15 plan)."""
    modules = _imported_modules(path)
    own_module_stem = path.stem
    cross_capability_imports = {
        m
        for m in modules
        if m.startswith("atlas.capabilities.")
        and not m.endswith(".base")
        and not m.endswith(f".{own_module_stem}")
    }
    assert not cross_capability_imports, (
        f"{path} imports another capability module: {cross_capability_imports}"
    )


def test_capabilities_package_never_imported_by_clients() -> None:
    """atlas/capabilities/ is Atlas-internal -- clients only ever see Atlas.

    The one carve-out is ``atlas.capabilities.base`` (the ``CapabilityName``
    naming enum): it contains no capability logic, only the shared naming
    also used by the adapter manifest (§3.0/§5.1 of the Phase 15 plan), so
    the CLI adapter is allowed to import it for ``negotiate()``.
    """
    for path in _iter_py_files(CLIENTS_ROOT):
        modules = _imported_modules(path)
        forbidden = {
            m
            for m in modules
            if m.startswith("atlas.capabilities") and not m.endswith(".base")
        }
        assert not forbidden, f"{path} imports atlas.capabilities: {forbidden}"


def test_cli_application_still_never_imports_engine() -> None:
    cli_app = CLIENTS_ROOT / "cli" / "application.py"
    modules = _imported_modules(cli_app)
    forbidden = {m for m in modules if m == "engine" or m.startswith("engine.")}
    assert not forbidden, f"{cli_app} imports engine modules: {forbidden}"
