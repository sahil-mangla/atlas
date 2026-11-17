"""The engine and shared layers import nothing above them.

The other directions (clients, presentation, capabilities) are covered by
the neighbouring boundary tests; together they back the layer table in
CONTRIBUTING.md.
"""

import ast
from pathlib import Path

import pytest

from tests.architecture.layers import ROOT, layer_module

PACKAGE = Path(__file__).resolve().parents[2] / ROOT
ALLOWED = {
    "engine": {"engine", "shared"},
    "shared": {"shared"},
}


def _layer_imports(path: Path) -> set[str]:
    layers: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        else:
            continue
        layers.update(
            layer_module(name).split(".")[0] for name in names if name.startswith(ROOT)
        )
    return layers


@pytest.mark.parametrize("layer", sorted(ALLOWED))
def test_layer_imports_only_itself_and_below(layer: str) -> None:
    violations = {
        str(path.relative_to(PACKAGE)): sorted(found - ALLOWED[layer])
        for path in sorted((PACKAGE / layer).rglob("*.py"))
        if (found := _layer_imports(path)) - ALLOWED[layer]
    }

    assert not violations, f"{layer} imports layers above it: {violations}"
