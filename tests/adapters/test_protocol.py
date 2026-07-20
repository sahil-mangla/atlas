"""Tests for atlas.adapters.protocol -- the platform adapter structural contract."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from atlas.adapters.protocol import (
    AdapterContext,
    AdapterKind,
    PlatformAdapter,
    PlatformCapabilityManifest,
)
from atlas.capabilities.base import CapabilityName
from atlas.contracts.version import PLATFORM_API_VERSION
from clients.cli.application import CLIApplication


def test_adapter_context_is_frozen() -> None:
    context = AdapterContext(kind=AdapterKind.CLI, name="atlas-cli", version="1.0.0")
    with pytest.raises(ValidationError):
        context.version = "2.0.0"


def test_platform_capability_manifest_uses_capability_name_enum() -> None:
    manifest = PlatformCapabilityManifest(
        api_version="1.0.0", capabilities=(CapabilityName.PROJECT,)
    )
    assert manifest.capabilities == (CapabilityName.PROJECT,)
    with pytest.raises(ValidationError):
        manifest.capabilities = ()


def test_platform_capability_manifest_rejects_unknown_capability_name() -> None:
    """The enum typing catches typos/unknown capability names at construction
    time -- a raw string matching a real member (e.g. "project") still
    coerces via StrEnum, but an invalid one must fail validation."""
    with pytest.raises(ValidationError):
        PlatformCapabilityManifest(
            api_version="1.0.0",
            capabilities=("not_a_real_capability",),  # type: ignore[arg-type]
        )


def test_arbitrary_object_does_not_satisfy_platform_adapter() -> None:
    class NotAnAdapter:
        pass

    assert not isinstance(NotAnAdapter(), PlatformAdapter)


def _cli_app() -> CLIApplication:
    return CLIApplication(atlas_platform=MagicMock())


def test_cli_application_satisfies_platform_adapter() -> None:
    assert isinstance(_cli_app(), PlatformAdapter)


def test_cli_application_context_is_cli_kind() -> None:
    app = _cli_app()
    assert app.context.kind == AdapterKind.CLI
    assert app.context.name == "atlas-cli"


def test_cli_application_negotiate_returns_all_five_capabilities() -> None:
    app = _cli_app()
    manifest = app.negotiate(app._atlas)
    assert manifest.api_version == PLATFORM_API_VERSION
    assert manifest.capabilities == (
        CapabilityName.PROJECT,
        CapabilityName.WORKFLOW,
        CapabilityName.WORKFLOW_EXECUTION,
        CapabilityName.KNOWLEDGE,
        CapabilityName.PRESENTATION,
    )
