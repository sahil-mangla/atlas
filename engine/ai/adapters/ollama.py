"""Adapter for Ollama's local generation protocol."""

from typing import Any

from engine.ai.adapters._http import post_json
from engine.ai.config import ProviderConfig
from engine.ai.exceptions import AIProviderException
from engine.ai.provider import AIProvider
from engine.domain.ai import AIRequest, AIResponse, ProviderCapabilities


class OllamaAIProvider(AIProvider):
    """Execute the same normalized requests against a local Ollama server."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config

    def generate(self, request: AIRequest) -> AIResponse:
        if not self._config.model:
            raise AIProviderException("Ollama protocol requires a model.")
        endpoint = (self._config.endpoint or "http://localhost:11434").rstrip("/")
        options: dict[str, Any] = request.parameters.model_dump(exclude_none=True)
        if request.parameters.max_output_tokens is not None:
            options["num_predict"] = options.pop("max_output_tokens")
        payload: dict[str, Any] = {
            "model": self._config.model,
            "prompt": request.prompt.user_prompt,
            "system": request.prompt.system_prompt,
            "stream": False,
            "options": options,
        }
        if request.response_schema is not None:
            payload["format"] = "json"
        payload.update(self._config.options)
        data = post_json(
            endpoint + "/api/generate",
            payload,
            {},
            timeout=self._config.timeout_seconds,
        )
        return AIResponse(
            content=str(data.get("response", "")),
            usage_metrics={
                "prompt_tokens": int(data.get("prompt_eval_count", 0)),
                "completion_tokens": int(data.get("eval_count", 0)),
            },
            finish_reason=str(data.get("done_reason", "unknown")),
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            structured_output=True,
            streaming_support=False,
            tool_calling=False,
            image_input=False,
            reasoning_support=False,
            context_window=int(self._config.options.get("context_window", 32768)),
        )
