import os
from pathlib import Path


def test_no_ai_imports_in_knowledge() -> None:
    """Ensure engine/knowledge does not import engine/ai (except domain models)."""
    knowledge_dir = "engine/knowledge"
    for root, _, files in os.walk(knowledge_dir):
        for f in files:
            if not f.endswith(".py"):
                continue
            path = Path(root) / f
            with path.open() as file:
                content = file.read()
                assert "from engine.ai." not in content, f"Found AI import in {path}"
                assert "import engine.ai" not in content, f"Found AI import in {path}"


def test_no_knowledge_imports_in_ai() -> None:
    """Ensure engine/ai does not import engine/knowledge (except domain models/SDK)."""
    ai_dir = "engine/ai"
    for root, _, files in os.walk(ai_dir):
        for f in files:
            if not f.endswith(".py"):
                continue
            path = Path(root) / f
            with path.open() as file:
                content = file.read()
                # Context integration uses EngineeringKnowledgeContext from
                # domain, not from engine.knowledge
                assert "from engine.knowledge." not in content, (
                    f"Found Knowledge subsystem import in {path}"
                )
                assert "import engine.knowledge" not in content, (
                    f"Found Knowledge subsystem import in {path}"
                )
