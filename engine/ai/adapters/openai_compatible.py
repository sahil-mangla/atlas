"""Adapter for any service implementing the OpenAI chat-completions protocol."""

from typing import Any

from engine.ai.adapters._http import post_json
from engine.ai.config import ProviderConfig
from engine.ai.exceptions import AIProviderException
from engine.ai.provider import AIProvider
from engine.domain.ai import (
    AIGenerationParameters,
    AIRequest,
    AIResponse,
    ProviderCapabilities,
)


class OpenAICompatibleAIProvider(AIProvider):
    """Execute requests against OpenAI-compatible cloud or local endpoints."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config

    def generate(self, request: AIRequest) -> AIResponse:
        if not self._config.endpoint or not self._config.model:
            raise AIProviderException(
                "OpenAI-compatible protocol requires endpoint and model."
            )
        messages = [
            {"role": "system", "content": request.prompt.system_prompt},
            {"role": "user", "content": request.prompt.user_prompt},
        ]
        payload: dict[str, Any] = {"model": self._config.model, "messages": messages}
        if request.response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": str(request.response_schema.get("title", "response")),
                    "schema": request.response_schema,
                },
            }
        payload.update(self._normalize_parameters(request.parameters))
        payload.update(self._config.options)
        headers = (
            {"Authorization": f"Bearer {self._config.api_key}"}
            if self._config.api_key
            else {}
        )
        data = post_json(
            self._config.endpoint.rstrip("/") + "/chat/completions", payload, headers
        )
        choices = data.get("choices", [])
        first = choices[0] if choices else {}
        message = first.get("message", {}) if isinstance(first, dict) else {}
        usage = data.get("usage", {}) if isinstance(data.get("usage"), dict) else {}
        return AIResponse(
            content=str(message.get("content", "")),
            usage_metrics={
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
            },
            finish_reason=str(first.get("finish_reason", "unknown")),
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            structured_output=True,
            streaming_support=False,
            tool_calling=False,
            image_input=False,
            reasoning_support=False,
            context_window=int(self._config.options.get("context_window", 128000)),
        )

    @staticmethod
    def _normalize_parameters(parameters: AIGenerationParameters) -> dict[str, Any]:
        """Map ATLAS generation parameters to OpenAI chat-completions fields."""
        payload: dict[str, Any] = {}
        if parameters.temperature is not None:
            payload["temperature"] = parameters.temperature
        if parameters.top_p is not None:
            payload["top_p"] = parameters.top_p
        if parameters.max_output_tokens is not None:
            payload["max_tokens"] = parameters.max_output_tokens
        return payload
