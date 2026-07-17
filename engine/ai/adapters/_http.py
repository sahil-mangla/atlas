"""Small standard-library HTTP helpers shared by protocol adapters."""

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from engine.ai.exceptions import AIProviderException


def post_json(
    url: str, payload: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any]:
    """Send a JSON request and normalize transport errors to runtime errors."""
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result: object = json.loads(response.read())
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as error:
        raise AIProviderException(f"AI protocol request failed: {error}") from error
    if not isinstance(result, dict):
        raise AIProviderException("AI protocol returned a non-object JSON response.")
    return result
