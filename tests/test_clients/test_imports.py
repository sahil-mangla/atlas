"""Tests for import isolation in the client adapter layer."""

import ast
import pathlib


def test_clients_do_not_import_engine() -> None:
    """Verify that the clients package never imports from engine directly."""
    # Find all Python files in the clients directory
    project_root = pathlib.Path(__file__).parent.parent.parent
    clients_dir = project_root / "clients"

    violations = []

    for py_file in clients_dir.rglob("*.py"):
        content = py_file.read_text()
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name == "engine" or name.name.startswith("engine."):
                        violations.append(f"{py_file.name}: imports {name.name}")
            elif isinstance(node, ast.ImportFrom):  # noqa: SIM102
                if node.module and (
                    node.module == "engine" or node.module.startswith("engine.")
                ):
                    violations.append(f"{py_file.name}: imports from {node.module}")

    assert not violations, "Found boundary violations in clients:\n" + "\n".join(
        violations
    )
