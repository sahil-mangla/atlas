"""Protocol adapters exercised over real HTTP against a loopback fake server.

The other adapter tests replace ``post_json`` with a mock, so they never run
the actual transport: URL building, headers, JSON encoding, status handling
and timeouts. These tests send genuine requests to a server on 127.0.0.1
that speaks just enough of each provider's wire format, which covers that
gap without any provider account or outbound network access.
"""

import json
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from atlas_eng.engine.ai.adapters._http import post_json
from atlas_eng.engine.ai.adapters.anthropic import AnthropicAIProvider
from atlas_eng.engine.ai.adapters.ollama import (
    OllamaAIProvider,
    OllamaEmbeddingProvider,
)
from atlas_eng.engine.ai.adapters.openai_compatible import (
    OpenAICompatibleAIProvider,
    OpenAICompatibleEmbeddingProvider,
)
from atlas_eng.engine.ai.adapters.scripted import ScriptedAIProvider
from atlas_eng.engine.ai.config import ProviderConfig
from atlas_eng.engine.ai.context import IdentityContextStrategy
from atlas_eng.engine.ai.exceptions import AIProviderException
from atlas_eng.engine.ai.executor import PromptExecutor
from atlas_eng.engine.ai.provider import AIProvider
from atlas_eng.engine.domain.ai import AIRequest, ContextPayload
from atlas_eng.engine.domain.ai_drafts import PlanningProposalDraft
from atlas_eng.engine.domain.prompt_document import PromptDocument
from atlas_eng.engine.prompt.templates import PlanningPromptTemplate

Responder = Callable[[str, dict[str, Any]], tuple[int, bytes]]


def _planning_json() -> str:
    """A valid planning draft, borrowed from the scripted provider."""
    request = AIRequest(
        prompt=PromptDocument(system_prompt="s", context="", task="t"),
        context=ContextPayload(serialized_context=""),
        response_schema=PlanningProposalDraft.model_json_schema(),
    )
    return ScriptedAIProvider().generate(request).content


def _ok(body: dict[str, Any]) -> tuple[int, bytes]:
    return 200, json.dumps(body).encode()


def _speak_provider_protocols(path: str, payload: dict[str, Any]) -> tuple[int, bytes]:
    """Answer each supported endpoint in that provider's response shape."""
    draft = _planning_json()
    if path == "/v1/chat/completions":
        return _ok(
            {
                "choices": [{"message": {"content": draft}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7},
            }
        )
    if path == "/api/generate":
        return _ok(
            {
                "response": draft,
                "done_reason": "stop",
                "prompt_eval_count": 11,
                "eval_count": 7,
            }
        )
    if path == "/v1/messages":
        return _ok(
            {
                "content": [
                    {"type": "thinking", "thinking": "..."},
                    {"type": "text", "text": draft},
                ],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 11, "output_tokens": 7},
            }
        )
    if path == "/v1/embeddings":
        inputs = payload["input"]
        # Returned out of order on purpose: the adapter must sort by index.
        data = [
            {"index": index, "embedding": [float(index), 1.0]}
            for index in reversed(range(len(inputs)))
        ]
        return _ok({"data": data})
    if path == "/api/embed":
        count = len(payload["input"])
        return _ok({"embeddings": [[float(i), 1.0] for i in range(count)]})
    return 404, b'{"error": "not found"}'


@dataclass
class FakeProviderServer:
    """A loopback HTTP server recording every request it receives."""

    base_url: str
    requests: list[tuple[str, dict[str, str], dict[str, Any]]] = field(
        default_factory=list
    )
    responder: Responder = _speak_provider_protocols

    @property
    def last_path(self) -> str:
        return self.requests[-1][0]

    @property
    def last_headers(self) -> dict[str, str]:
        return self.requests[-1][1]

    @property
    def last_payload(self) -> dict[str, Any]:
        return self.requests[-1][2]


@pytest.fixture
def server() -> Iterator[FakeProviderServer]:
    fake = FakeProviderServer(base_url="")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            headers = {key.lower(): value for key, value in self.headers.items()}
            fake.requests.append((self.path, headers, payload))
            status, body = fake.responder(self.path, payload)
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                # The client gave up first (the timeout test does this).
                pass

        def log_message(self, *_args: object) -> None:
            """Keep test output quiet."""

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    fake.base_url = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        yield fake
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _run_planning_stage(provider: AIProvider) -> PlanningProposalDraft:
    executor = PromptExecutor(provider, IdentityContextStrategy())
    return executor.execute(
        PlanningPromptTemplate(),
        ContextPayload(serialized_context="project context"),
        PlanningProposalDraft,
    )


def _plain_request() -> AIRequest:
    return AIRequest(
        prompt=PromptDocument(system_prompt="system", context="ctx", task="task"),
        context=ContextPayload(serialized_context="ctx"),
    )


def test_openai_compatible_runs_a_stage_over_http(server: FakeProviderServer) -> None:
    provider = OpenAICompatibleAIProvider(
        ProviderConfig(
            protocol="OPENAI_COMPATIBLE",
            # Trailing slash on purpose: the adapter must not double it.
            endpoint=server.base_url + "/v1/",
            model="test-model",
            api_key="sk-test",
        )
    )

    draft = _run_planning_stage(provider)

    assert draft.scope_statement
    assert server.last_path == "/v1/chat/completions"
    assert server.last_headers["authorization"] == "Bearer sk-test"
    assert server.last_headers["content-type"] == "application/json"
    assert server.last_payload["model"] == "test-model"
    schema = server.last_payload["response_format"]["json_schema"]
    assert schema["name"] == "PlanningProposalDraft"


def test_openai_compatible_sends_no_auth_header_without_a_key(
    server: FakeProviderServer,
) -> None:
    """Local servers such as LM Studio take no key at all."""
    provider = OpenAICompatibleAIProvider(
        ProviderConfig(
            protocol="OPENAI_COMPATIBLE", endpoint=server.base_url + "/v1", model="m"
        )
    )

    provider.generate(_plain_request())

    assert "authorization" not in server.last_headers


def test_ollama_runs_a_stage_over_http(server: FakeProviderServer) -> None:
    provider = OllamaAIProvider(
        ProviderConfig(protocol="OLLAMA", endpoint=server.base_url, model="local")
    )

    draft = _run_planning_stage(provider)

    assert draft.deliverables
    assert server.last_path == "/api/generate"
    assert server.last_payload["stream"] is False
    assert server.last_payload["format"]["title"] == "PlanningProposalDraft"


def test_anthropic_generates_over_http_and_skips_non_text_blocks(
    server: FakeProviderServer,
) -> None:
    provider = AnthropicAIProvider(
        ProviderConfig(
            protocol="ANTHROPIC",
            endpoint=server.base_url + "/v1/messages",
            model="test-model",
            api_key="sk-ant-test",
        )
    )

    response = provider.generate(_plain_request())

    PlanningProposalDraft.model_validate_json(response.content)
    assert response.usage_metrics == {"prompt_tokens": 11, "completion_tokens": 7}
    assert server.last_headers["x-api-key"] == "sk-ant-test"
    assert server.last_headers["anthropic-version"]
    assert server.last_payload["max_tokens"] > 0


def test_anthropic_can_run_a_stage(server: FakeProviderServer) -> None:
    provider = AnthropicAIProvider(
        ProviderConfig(
            protocol="ANTHROPIC",
            endpoint=server.base_url + "/v1/messages",
            model="test-model",
            api_key="sk-ant-test",
        )
    )

    assert _run_planning_stage(provider).scope_statement
    output_format = server.last_payload["output_config"]["format"]
    assert output_format["type"] == "json_schema"
    assert _objects_missing_closed_properties(output_format["schema"]) == []


def _objects_missing_closed_properties(schema: Any, path: str = "$") -> list[str]:
    """Paths of object schemas that do not set ``additionalProperties: false``.

    Anthropic rejects the whole request if any object, however deeply nested,
    leaves it out.
    """
    if isinstance(schema, list):
        return [
            missing
            for index, item in enumerate(schema)
            for missing in _objects_missing_closed_properties(item, f"{path}[{index}]")
        ]
    if not isinstance(schema, dict):
        return []
    missing = [
        found
        for key, value in schema.items()
        for found in _objects_missing_closed_properties(value, f"{path}.{key}")
    ]
    if (
        schema.get("type") == "object"
        and schema.get("additionalProperties") is not False
    ):
        missing.append(path)
    return missing


def test_openai_compatible_embeddings_are_reordered_by_index(
    server: FakeProviderServer,
) -> None:
    embedder = OpenAICompatibleEmbeddingProvider(
        ProviderConfig(
            protocol="OPENAI_COMPATIBLE", endpoint=server.base_url + "/v1", model="e"
        )
    )

    vectors = embedder.embed(["a", "b", "c"])

    assert [vector[0] for vector in vectors] == [0.0, 1.0, 2.0]
    assert server.last_path == "/v1/embeddings"


def test_ollama_embeddings_over_http(server: FakeProviderServer) -> None:
    embedder = OllamaEmbeddingProvider(
        ProviderConfig(protocol="OLLAMA", endpoint=server.base_url, model="e")
    )

    assert len(embedder.embed(["a", "b"])) == 2
    assert server.last_path == "/api/embed"


@pytest.mark.parametrize("status", [401, 403])
def test_auth_failures_tell_the_user_to_check_the_key(
    server: FakeProviderServer, status: int
) -> None:
    server.responder = lambda _path, _payload: (status, b'{"error": "denied"}')

    with pytest.raises(AIProviderException, match="API key"):
        post_json(server.base_url + "/x", {}, {})


@pytest.mark.parametrize("status", [400, 404, 429, 500, 503])
def test_http_errors_are_reported_with_their_status(
    server: FakeProviderServer, status: int
) -> None:
    server.responder = lambda _path, _payload: (status, b'{"error": "nope"}')

    with pytest.raises(AIProviderException, match=str(status)):
        post_json(server.base_url + "/x", {}, {})


@pytest.mark.parametrize(
    "body",
    [b"<html>502 Bad Gateway</html>", b"", b'{"truncated": ', b"[1, 2, 3]", b'"text"'],
    ids=["html", "empty", "truncated-json", "json-array", "json-string"],
)
def test_unusable_response_bodies_raise_provider_errors(
    server: FakeProviderServer, body: bytes
) -> None:
    server.responder = lambda _path, _payload: (200, body)

    with pytest.raises(AIProviderException):
        post_json(server.base_url + "/x", {}, {})


def test_slow_provider_times_out_with_actionable_advice(
    server: FakeProviderServer,
) -> None:
    def slow(_path: str, _payload: dict[str, Any]) -> tuple[int, bytes]:
        time.sleep(3)
        return 200, b"{}"

    server.responder = slow
    started = time.monotonic()

    with pytest.raises(AIProviderException, match="ATLAS_AI_TIMEOUT_SECONDS"):
        post_json(server.base_url + "/x", {}, {}, timeout=1)

    assert time.monotonic() - started < 3


def test_unreachable_provider_is_a_provider_error() -> None:
    # Port 1 on loopback is never listening; the connection is refused at once.
    with pytest.raises(AIProviderException):
        post_json("http://127.0.0.1:1/x", {}, {}, timeout=2)


def test_malformed_stage_output_from_a_real_endpoint_is_rejected(
    server: FakeProviderServer,
) -> None:
    """A model that ignores the schema must not produce a committed proposal."""
    server.responder = lambda _path, _payload: _ok(
        {"response": "Here is your plan!", "done_reason": "stop"}
    )
    provider = OllamaAIProvider(
        ProviderConfig(protocol="OLLAMA", endpoint=server.base_url, model="local")
    )

    with pytest.raises(Exception, match="Failed to parse generation"):
        _run_planning_stage(provider)
