"""Small standard-library HTTP helpers shared by protocol adapters."""

import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from engine.ai.exceptions import AIProviderException

logger = logging.getLogger(__name__)


def post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int = 60,
) -> dict[str, Any]:
    """Send a JSON request and normalize transport errors to runtime errors."""
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    started_at = time.monotonic()
    try:
        with urlopen(request, timeout=timeout) as response:
            result: object = json.loads(response.read())
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as error:
        elapsed = time.monotonic() - started_at
        logger.info("AI request to %s failed after %.1fs: %s", url, elapsed, error)
        raise AIProviderException(f"AI protocol request failed: {error}") from error
    elapsed = time.monotonic() - started_at
    logger.info("AI request to %s completed in %.1fs", url, elapsed)
    if not isinstance(result, dict):
        raise AIProviderException("AI protocol returned a non-object JSON response.")
    return result
