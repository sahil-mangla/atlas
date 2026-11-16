"""Adapter for Anthropic's Messages protocol."""

from typing import Any

from langfuse.decorators import langfuse_context, observe

from atlas_eng.engine.ai.adapters._http import post_json
from atlas_eng.engine.ai.config import ProviderConfig
from atlas_eng.engine.ai.exceptions import AIProviderException
from atlas_eng.engine.ai.provider import AIProvider
from atlas_eng.engine.domain.ai import AIRequest, AIResponse, ProviderCapabilities

# Non-streaming requests must stay under HTTP timeouts, but a stage draft is
# long structured JSON: too small a cap truncates it mid-object.
_DEFAULT_MAX_TOKENS = 16000

# JSON-schema keywords Anthropic's structured outputs reject. The draft is
# validated against the full pydantic model afterwards, so dropping them from
# the wire schema loses no checking.
_UNSUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "pattern",
        "minItems",
        "maxItems",
        "uniqueItems",
    }
)


def to_structured_output_schema(schema: Any) -> Any:
    """Adapt a pydantic JSON schema to Anthropic's structured-output subset.

    Every object must set ``additionalProperties: false``, and numeric,
    string and array constraints are not accepted.
    """
    if isinstance(schema, list):
        return [to_structured_output_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    adapted = {
        key: to_structured_output_schema(value)
        for key, value in schema.items()
        if key not in _UNSUPPORTED_SCHEMA_KEYWORDS
    }
    if adapted.get("type") == "object":
        adapted["additionalProperties"] = False
    return adapted


class AnthropicAIProvider(AIProvider):
    """Execute standardized ATLAS requests via Anthropic Messages."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config

    @observe(
        as_type="generation",
        name="anthropic_generate",
        capture_input=False,
        capture_output=False,
    )
    def generate(self, request: AIRequest) -> AIResponse:
        if not self._config.model or not self._config.api_key:
            raise AIProviderException("Anthropic protocol requires api_key and model.")
        endpoint = self._config.endpoint or "https://api.anthropic.com/v1/messages"
        payload: dict[str, Any] = {
            "model": self._config.model,
            "system": request.prompt.system_prompt,
            "messages": [{"role": "user", "content": request.prompt.user_prompt}],
            "max_tokens": request.parameters.max_output_tokens or _DEFAULT_MAX_TOKENS,
        }
        if request.response_schema is not None:
            payload["output_config"] = {
                "format": {
                    "type": "json_schema",
                    "schema": to_structured_output_schema(request.response_schema),
                }
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

        content_str = str(first.get("text", ""))
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))

        langfuse_context.update_current_observation(
            model=self._config.model,
            input=[
                {"role": "system", "content": request.prompt.system_prompt},
                {"role": "user", "content": request.prompt.user_prompt},
            ],
            output=content_str,
            usage={"input": prompt_tokens, "output": completion_tokens},
        )

        return AIResponse(
            content=content_str,
            usage_metrics={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
            finish_reason=str(data.get("stop_reason", "unknown")),
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            structured_output=True,
            streaming_support=False,
            tool_calling=False,
            image_input=False,
            reasoning_support=False,
            context_window=int(self._config.options.get("context_window", 200000)),
        )
