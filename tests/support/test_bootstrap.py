"""Test-suite entry point for the offline platform in ``atlas.testing``.

Kept so existing tests retain their historical default provider: a
``MockAIProvider`` stubbed with ``"{}"`` rather than the scripted drafts.
"""

from pathlib import Path

from atlas_eng import Atlas
from atlas_eng.engine.ai.provider import AIProvider
from atlas_eng.observability.exporter import TraceExporter
from atlas_eng.testing import create_test_platform as _create_test_platform
from tests.ai.test_adapters import MockAIProvider


def create_test_platform(
    tmp_path: Path,
    ai_provider: AIProvider | None = None,
    *,
    instrumentation_enabled: bool = True,
    exporter: TraceExporter | None = None,
) -> Atlas:
    """Build the offline platform, defaulting to the legacy ``{}`` stub."""
    return _create_test_platform(
        tmp_path,
        ai_provider or MockAIProvider(stubbed_response="{}"),
        instrumentation_enabled=instrumentation_enabled,
        exporter=exporter,
    )
