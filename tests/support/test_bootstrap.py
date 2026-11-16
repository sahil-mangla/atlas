"""Test-suite entry point for the offline platform in ``atlas.testing``.

Kept so existing tests retain their historical default provider: a
``MockAIProvider`` stubbed with ``"{}"`` rather than the scripted drafts.
"""

from pathlib import Path

from atlas import Atlas
from atlas.observability.exporter import TraceExporter
from atlas.testing import create_test_platform as _create_test_platform
from engine.ai.provider import AIProvider
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
