"""Tests for error mapping in CLI adapter.

(Testing that the renderer handles exceptions gracefully and that CLIParseError is robust.)
"""  # noqa: E501

import pytest

from clients.cli.parser import CLIParseError, _uuid


def test_uuid_parsing_error() -> None:
    with pytest.raises(CLIParseError, match="not a valid UUID"):
        _uuid("bad-uuid")


def test_cli_parse_error_is_value_error() -> None:
    assert issubclass(CLIParseError, ValueError)
