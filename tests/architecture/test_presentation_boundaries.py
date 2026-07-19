"""Static import-boundary guard for the Phase 14 presentation layer.

Verifies the locked dependency direction:

    Platform / Clients -> Atlas Facade -> PlatformOrchestrationService
    -> Collectors -> Typed Atlas Read Models -> Phase 1-13 services

Presentation must never import engine internals, repositories, persistence,
or the filesystem, and must never bypass the public `atlas` package.
"""

import ast
from pathlib import Path

import pytest

PRESENTATION_ROOT = Path(__file__).resolve().parents[2] / "presentation"

FORBIDDEN_PREFIXES = (
    "engine.",
    "engine",
)
FORBIDDEN_EXACT_MODULES = {
    "sqlite3",
    "sqlalchemy",
}


def _iter_presentation_files() -> list[Path]:
    return sorted(PRESENTATION_ROOT.rglob("*.py"))


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize(
    "path",
    _iter_presentation_files(),
    ids=lambda p: str(p.relative_to(PRESENTATION_ROOT)),
)
def test_presentation_module_has_no_engine_imports(path: Path) -> None:
    modules = _imported_modules(path)
    violations = {
        m
        for m in modules
        if m in FORBIDDEN_EXACT_MODULES
        or any(
            m == prefix.rstrip(".") or m.startswith(prefix)
            for prefix in FORBIDDEN_PREFIXES
        )
    }
    assert not violations, (
        f"{path} imports forbidden engine/persistence modules: {violations}"
    )


@pytest.mark.parametrize(
    "path",
    _iter_presentation_files(),
    ids=lambda p: str(p.relative_to(PRESENTATION_ROOT)),
)
def test_presentation_module_only_imports_atlas_publicly(path: Path) -> None:
    modules = _imported_modules(path)
    private_atlas_imports = {
        m for m in modules if m == "atlas._service" or m.startswith("atlas._")
    }
    assert not private_atlas_imports, (
        f"{path} imports Atlas via a private module: {private_atlas_imports}. Import `from atlas import Atlas` instead."
    )


def test_renderers_never_import_atlas() -> None:
    renderer_files = sorted((PRESENTATION_ROOT / "renderers").rglob("*.py"))
    assert renderer_files, "expected renderer modules to exist"
    for path in renderer_files:
        modules = _imported_modules(path)
        atlas_imports = {m for m in modules if m == "atlas" or m.startswith("atlas.")}
        assert not atlas_imports, (
            f"{path} (a renderer) must never import atlas: {atlas_imports}"
        )


def test_components_never_import_atlas_or_engine() -> None:
    component_files = sorted((PRESENTATION_ROOT / "components").rglob("*.py"))
    assert component_files, "expected component modules to exist"
    for path in component_files:
        modules = _imported_modules(path)
        forbidden = {
            m
            for m in modules
            if m == "atlas"
            or m.startswith("atlas.")
            or m == "engine"
            or m.startswith("engine.")
        }
        assert not forbidden, (
            f"{path} (a component) must never import atlas or engine: {forbidden}"
        )


def test_views_never_import_atlas_or_engine() -> None:
    view_files = sorted((PRESENTATION_ROOT / "views").rglob("*.py"))
    assert view_files, "expected view modules to exist"
    for path in view_files:
        modules = _imported_modules(path)
        forbidden = {
            m
            for m in modules
            if m == "atlas"
            or m.startswith("atlas.")
            or m == "engine"
            or m.startswith("engine.")
        }
        assert not forbidden, (
            f"{path} (a view) must never import atlas or engine: {forbidden}"
        )


def test_no_presentation_module_imports_repository_or_filesystem_symbols() -> None:
    banned_substrings = ("repository", "fs_repository", "filesystem", "persistence")
    for path in _iter_presentation_files():
        modules = _imported_modules(path)
        for module in modules:
            lowered = module.lower()
            assert not any(b in lowered for b in banned_substrings), (
                f"{path} imports a persistence-flavored module: {module}"
            )
