"""Tests for atlas.contracts.version -- API version compatibility policy."""

from atlas.contracts.version import PLATFORM_API_VERSION, SCHEMA_VERSION, is_compatible


def test_platform_api_version_is_semver_string() -> None:
    assert PLATFORM_API_VERSION == "1.0.0"


def test_schema_version_is_integer() -> None:
    assert SCHEMA_VERSION == 1


def test_same_version_is_compatible() -> None:
    assert is_compatible("1.0.0") is True


def test_same_major_different_minor_patch_is_compatible() -> None:
    assert is_compatible("1.4.2") is True


def test_different_major_is_incompatible() -> None:
    assert is_compatible("2.0.0") is False
