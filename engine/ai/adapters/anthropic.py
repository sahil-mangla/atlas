"""Adapter for Anthropic's Messages protocol."""

from typing import Any

from engine.ai.adapters._http import post_json
from engine.ai.config import ProviderConfig
from engine.ai.exceptions import AIProviderException
from engine.ai.provider import AIProvider
from engine.domain.ai import AIRequest, AIResponse, ProviderCapabilities


class AnthropicAIProvider(AIProvider):
    """Execute standardized ATLAS requests via Anthropic Messages."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config

    def generate(self, request: AIRequest) -> AIResponse:
        if not self._config.model or not self._config.api_key:
            raise AIProviderException("Anthropic protocol requires api_key and model.")
        endpoint = self._config.endpoint or "https://api.anthropic.com/v1/messages"
        payload: dict[str, Any] = {
            "model": self._config.model,
            "system": request.prompt.system_prompt,
            "messages": [{"role": "user", "content": request.prompt.user_prompt}],
            "max_tokens": request.parameters.max_output_tokens or 4096,
        }
        payload.update(
            {
                key: value
                for key, value in request.parameters.model_dump(
                    exclude_none=True
                ).items()
                if key != "max_output_tokens"
            }
        )
        payload.update(self._config.options)
        data = post_json(
            endpoint,
            payload,
            {"x-api-key": self._config.api_key, "anthropic-version": "2023-06-01"},
            timeout=self._config.timeout_seconds,
        )
        content = data.get("content", [])
        # Anthropic responses can include non-text blocks first (e.g. a
        # "thinking" block, reachable when extended-thinking config is
        # merged in via self._config.options) -- blindly using content[0]
        # would silently return "" for the actual text. Text blocks carry a
        # "text" field; other block types don't.
        first: dict[str, Any] = next(
            (block for block in content if "text" in block), {}
        )
        usage = data.get("usage", {})
        return AIResponse(
            content=str(first.get("text", "")),
            usage_metrics={
                "prompt_tokens": int(usage.get("input_tokens", 0)),
                "completion_tokens": int(usage.get("output_tokens", 0)),
            },
            finish_reason=str(data.get("stop_reason", "unknown")),
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            structured_output=False,
            streaming_support=False,
            tool_calling=False,
            image_input=False,
            reasoning_support=False,
            context_window=int(self._config.options.get("context_window", 200000)),
        )
