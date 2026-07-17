"""Contract tests for the multi-protocol AI runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch
from urllib.error import URLError

import pytest
from pytest import MonkeyPatch

import atlas._bootstrap as bootstrap
from engine.ai.adapters._http import post_json
from engine.ai.adapters.anthropic import AnthropicAIProvider
from engine.ai.adapters.gemini import GeminiAIProvider
from engine.ai.adapters.ollama import OllamaAIProvider
from engine.ai.adapters.openai_compatible import OpenAICompatibleAIProvider
from engine.ai.config import ProviderConfig
from engine.ai.context import IdentityContextStrategy
from engine.ai.exceptions import AIProviderException
from engine.ai.executor import PromptExecutor
from engine.ai.factory import ProtocolFactory
from engine.ai.provider import AIProvider
from engine.config import Settings
from engine.domain.ai import (
    AIGenerationParameters,
    AIRequest,
    AIToolSchema,
    ContextPayload,
    ProviderCapabilities,
)
from engine.domain.ai_drafts import ResearchProposalDraft
from engine.domain.prompt_document import PromptDocument
from engine.prompt.templates import ResearchPromptTemplate
from tests.ai.test_adapters import MockAIProvider

_OPENAI_TEMPERATURE = 0.2
_OPENAI_TOP_P = 0.9
_OPENAI_MAX_TOKENS = 128
_ANTHROPIC_TEMPERATURE = 0.1
_ANTHROPIC_MAX_TOKENS = 256
_OLLAMA_NUM_PREDICT = 64


def _prompt_request(
    *,
    response_schema: dict[str, Any] | None = None,
    parameters: AIGenerationParameters | None = None,
    tools: list[AIToolSchema] | None = None,
) -> AIRequest:
    return AIRequest(
        prompt=PromptDocument(
            system_prompt="system",
            context="context",
            task="task",
        ),
        context=ContextPayload(serialized_context="context"),
        response_schema=response_schema,
        parameters=parameters or AIGenerationParameters(),
        tools=tools or [],
    )


def _unimplemented_capability_flags() -> dict[str, bool]:
    return {
        "streaming_support": False,
        "tool_calling": False,
        "image_input": False,
        "reasoning_support": False,
    }


@pytest.mark.parametrize(
    ("protocol", "adapter_type", "structured_output"),
    [
        ("GEMINI", GeminiAIProvider, True),
        ("OPENAI_COMPATIBLE", OpenAICompatibleAIProvider, True),
        ("ANTHROPIC", AnthropicAIProvider, False),
        ("OLLAMA", OllamaAIProvider, True),
    ],
)
def test_protocol_factory_resolves_registered_adapters(
    protocol: str, adapter_type: type[object], structured_output: bool
) -> None:
    provider = ProtocolFactory().resolve(
        ProviderConfig(
            protocol=protocol,
            endpoint="https://example.test/v1",
            model="test-model",
            api_key="test-key",
        )
    )

    assert isinstance(provider, adapter_type)
    capabilities = provider.capabilities()
    assert capabilities.structured_output is structured_output
    assert capabilities.context_window > 0
    for flag, expected in _unimplemented_capability_flags().items():
        assert getattr(capabilities, flag) is expected


@pytest.mark.parametrize(
    "vendor_endpoint",
    [
        "https://api.openai.com/v1",
        "https://api.groq.com/openai/v1",
        "https://api.together.xyz/v1",
        "https://openrouter.ai/api/v1",
        "http://localhost:1234/v1",
        "https://api.fireworks.ai/inference/v1",
        "http://localhost:8000/v1",
        "http://localhost:8080/v1",
    ],
)
def test_openai_compatible_vendors_need_configuration_only(
    vendor_endpoint: str,
) -> None:
    provider = ProtocolFactory().resolve(
        ProviderConfig(
            protocol="OPENAI_COMPATIBLE",
            endpoint=vendor_endpoint,
            model="configured-model",
            api_key="vendor-key",
        )
    )

    assert isinstance(provider, OpenAICompatibleAIProvider)
    assert provider.capabilities().structured_output is True


def test_protocol_factory_rejects_unknown_protocol() -> None:
    with pytest.raises(AIProviderException, match="Unknown AI Protocol: UNKNOWN"):
        ProtocolFactory().resolve(ProviderConfig(protocol="unknown"))


def test_protocol_factory_registry_is_immutable() -> None:
    factory = ProtocolFactory()

    with pytest.raises(TypeError):
        factory._registry["GEMINI"] = factory._registry["GEMINI"]  # type: ignore[index]


def test_openai_compatible_normalizes_request_and_response() -> None:
    provider = OpenAICompatibleAIProvider(
        ProviderConfig(
            protocol="OPENAI_COMPATIBLE",
            endpoint="https://api.openai.com/v1",
            model="gpt-test",
            api_key="secret",
        )
    )
    request = _prompt_request(
        response_schema={"type": "object"},
        parameters=AIGenerationParameters(
            temperature=_OPENAI_TEMPERATURE,
            top_p=_OPENAI_TOP_P,
            max_output_tokens=_OPENAI_MAX_TOKENS,
        ),
    )
    fake_response = {
        "choices": [
            {
                "message": {"content": '{"ok": true}'},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }

    with patch(
        "engine.ai.adapters.openai_compatible.post_json", return_value=fake_response
    ) as mocked_post:
        response = provider.generate(request)

    url, payload, headers = mocked_post.call_args.args
    assert url == "https://api.openai.com/v1/chat/completions"
    assert headers == {"Authorization": "Bearer secret"}
    assert payload["model"] == "gpt-test"
    assert payload["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": request.prompt.user_prompt},
    ]
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["temperature"] == _OPENAI_TEMPERATURE
    assert payload["top_p"] == _OPENAI_TOP_P
    assert payload["max_tokens"] == _OPENAI_MAX_TOKENS
    assert "max_output_tokens" not in payload
    assert response.content == '{"ok": true}'
    assert response.usage_metrics == {"prompt_tokens": 11, "completion_tokens": 7}
    assert response.finish_reason == "stop"


def test_anthropic_normalizes_request_and_response() -> None:
    provider = AnthropicAIProvider(
        ProviderConfig(
            protocol="ANTHROPIC",
            model="claude-test",
            api_key="secret",
        )
    )
    request = _prompt_request(
        parameters=AIGenerationParameters(
            temperature=_ANTHROPIC_TEMPERATURE,
            max_output_tokens=_ANTHROPIC_MAX_TOKENS,
        )
    )
    fake_response = {
        "content": [{"text": "hello"}],
        "usage": {"input_tokens": 3, "output_tokens": 2},
        "stop_reason": "end_turn",
    }

    with patch(
        "engine.ai.adapters.anthropic.post_json", return_value=fake_response
    ) as mocked_post:
        response = provider.generate(request)

    url, payload, headers = mocked_post.call_args.args
    assert url == "https://api.anthropic.com/v1/messages"
    assert headers["x-api-key"] == "secret"
    assert payload["model"] == "claude-test"
    assert payload["max_tokens"] == _ANTHROPIC_MAX_TOKENS
    assert payload["temperature"] == _ANTHROPIC_TEMPERATURE
    assert "max_output_tokens" not in payload
    assert response.content == "hello"
    assert response.usage_metrics == {"prompt_tokens": 3, "completion_tokens": 2}
    assert response.finish_reason == "end_turn"


def test_ollama_normalizes_request_and_response() -> None:
    provider = OllamaAIProvider(
        ProviderConfig(
            protocol="OLLAMA",
            model="llama-test",
            endpoint="http://localhost:11434",
        )
    )
    request = _prompt_request(
        response_schema={"type": "object"},
        parameters=AIGenerationParameters(max_output_tokens=_OLLAMA_NUM_PREDICT),
    )
    fake_response = {
        "response": '{"answer": 1}',
        "prompt_eval_count": 5,
        "eval_count": 4,
        "done_reason": "stop",
    }

    with patch(
        "engine.ai.adapters.ollama.post_json", return_value=fake_response
    ) as mocked_post:
        response = provider.generate(request)

    url, payload, _headers = mocked_post.call_args.args
    assert url == "http://localhost:11434/api/generate"
    assert payload["model"] == "llama-test"
    assert payload["format"] == "json"
    assert payload["options"]["num_predict"] == _OLLAMA_NUM_PREDICT
    assert "max_output_tokens" not in payload["options"]
    assert response.content == '{"answer": 1}'
    assert response.usage_metrics == {"prompt_tokens": 5, "completion_tokens": 4}
    assert response.finish_reason == "stop"


def test_http_helper_translates_transport_errors() -> None:
    with (
        patch(
            "engine.ai.adapters._http.urlopen",
            side_effect=URLError("offline"),
        ),
        pytest.raises(AIProviderException, match="AI protocol request failed"),
    ):
        post_json("http://example.test", {}, {})


def test_executor_rejects_unsupported_structured_output() -> None:
    provider = Mock(spec=AIProvider)
    provider.capabilities.return_value = ProviderCapabilities(
        structured_output=False,
        streaming_support=False,
        tool_calling=False,
        image_input=False,
        reasoning_support=False,
        context_window=1000,
    )
    executor = PromptExecutor(provider, IdentityContextStrategy())

    with pytest.raises(AIProviderException, match="structured_output"):
        executor.execute(
            ResearchPromptTemplate(),
            ContextPayload(serialized_context="context"),
            ResearchProposalDraft,
        )
    provider.generate.assert_not_called()


def test_executor_rejects_unsupported_tool_calling() -> None:
    provider = Mock(spec=AIProvider)
    provider.capabilities.return_value = ProviderCapabilities(
        structured_output=True,
        streaming_support=False,
        tool_calling=False,
        image_input=False,
        reasoning_support=False,
        context_window=1000,
    )
    executor = PromptExecutor(provider, IdentityContextStrategy())
    request = _prompt_request(
        tools=[
            AIToolSchema(
                name="lookup",
                description="lookup",
                parameters={"type": "object"},
            )
        ]
    )

    with pytest.raises(AIProviderException, match="tool_calling"):
        executor._require_supported_capabilities(request)


def test_executor_remains_protocol_independent() -> None:
    provider = MockAIProvider('{"problem_statement": "Problem", "objectives": []}')
    executor = PromptExecutor(provider, IdentityContextStrategy())

    draft = executor.execute(
        ResearchPromptTemplate(),
        ContextPayload(serialized_context="context"),
        ResearchProposalDraft,
    )

    assert draft.problem_statement == "Problem"


def _stub_bootstrap_services(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        bootstrap, "PromptLoader", Mock(load_registry=Mock(return_value=Mock()))
    )
    monkeypatch.setattr(bootstrap, "PromptExecutor", Mock(return_value=Mock()))
    monkeypatch.setattr(bootstrap, "AIOrchestrationService", Mock(return_value=Mock()))
    monkeypatch.setattr(
        bootstrap, "ResearchAIEngineeringService", Mock(return_value=Mock())
    )
    monkeypatch.setattr(
        bootstrap, "PlanningAIEngineeringService", Mock(return_value=Mock())
    )
    monkeypatch.setattr(
        bootstrap, "ArchitectureAIEngineeringService", Mock(return_value=Mock())
    )
    monkeypatch.setattr(
        bootstrap, "EvaluationAIEngineeringService", Mock(return_value=Mock())
    )
    monkeypatch.setattr(bootstrap, "ProposalCommitService", Mock(return_value=Mock()))
    monkeypatch.setattr(
        bootstrap, "WorkflowOrchestrationService", Mock(return_value=Mock())
    )
    monkeypatch.setattr(bootstrap, "Atlas", Mock(return_value=Mock()))


def test_runtime_configuration_switches_protocol(monkeypatch: MonkeyPatch) -> None:
    settings = Settings(
        ai_protocol="OPENAI_COMPATIBLE",
        ai_endpoint="https://api.groq.com/openai/v1",
        ai_model="llama-3",
        ai_api_key="groq-key",
    )
    captured: dict[str, Any] = {}

    def fake_resolve(
        _self: ProtocolFactory,
        config: ProviderConfig,
        _settings: Settings | None = None,
    ) -> AIProvider:
        captured["config"] = config
        return MockAIProvider("{}")

    monkeypatch.setattr(ProtocolFactory, "resolve", fake_resolve)
    monkeypatch.setattr(bootstrap, "get_settings", lambda: settings)
    _stub_bootstrap_services(monkeypatch)

    bootstrap._create_platform()

    config = captured["config"]
    assert config.protocol == "OPENAI_COMPATIBLE"
    assert config.endpoint == "https://api.groq.com/openai/v1"
    assert config.model == "llama-3"
    assert config.api_key == "groq-key"


def test_bootstrap_wires_protocol_factory_provider(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    provider = MockAIProvider("{}")
    resolve = Mock(return_value=provider)
    executor_ctor = Mock(return_value=Mock())

    monkeypatch.setattr(
        bootstrap, "get_settings", lambda: Settings(workspace_root=tmp_path)
    )
    monkeypatch.setattr(ProtocolFactory, "resolve", resolve)
    _stub_bootstrap_services(monkeypatch)
    monkeypatch.setattr(bootstrap, "PromptExecutor", executor_ctor)

    bootstrap._create_platform()

    resolve.assert_called_once()
    assert executor_ctor.call_args.args[0] is provider
