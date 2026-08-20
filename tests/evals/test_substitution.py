"""Tests for variable capture/substitution and dotted-path resolution."""

from uuid import uuid4

import pytest

from atlas.adapters.protocol import AdapterContext, AdapterKind
from atlas.commands import ListProjectsCommand
from atlas.contracts.envelope import RequestEnvelope, ResponseEnvelope
from atlas.results import ProjectListResult
from evals.substitution import (
    InvalidPathError,
    UnknownCaptureReferenceError,
    resolve_path,
    substitute,
)


def test_substitute_replaces_dollar_reference() -> None:
    assert substitute("$project_id", {"project_id": "abc"}) == "abc"


def test_substitute_leaves_plain_strings_alone() -> None:
    assert substitute("plain", {}) == "plain"


def test_substitute_recurses_into_dicts_and_lists() -> None:
    value = {"a": "$x", "b": ["$y", "literal"]}
    result = substitute(value, {"x": 1, "y": 2})
    assert result == {"a": 1, "b": [2, "literal"]}


def test_substitute_raises_on_unknown_reference() -> None:
    with pytest.raises(UnknownCaptureReferenceError):
        substitute("$missing", {})


def test_resolve_path_walks_result_attributes() -> None:
    envelope = RequestEnvelope(
        adapter=AdapterContext(kind=AdapterKind.AI, name="t", version="0"),
        command=ListProjectsCommand(),
    )
    response = ResponseEnvelope(
        request_id=envelope.request_id, result=ProjectListResult(projects=[])
    )
    assert resolve_path(response, "result.projects") == []


def test_resolve_path_reads_response_level_fields() -> None:
    request_id = uuid4()
    response = ResponseEnvelope(
        request_id=request_id, result=ProjectListResult(projects=[])
    )
    assert resolve_path(response, "response.request_id") == request_id


def test_resolve_path_rejects_unknown_root() -> None:
    with pytest.raises(InvalidPathError):
        resolve_path(object(), "bogus.field")
