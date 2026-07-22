"""Small standard-library HTTP helpers shared by protocol adapters."""

import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from engine.ai.exceptions import AIProviderException

logger = logging.getLogger(__name__)

_AUTH_ERROR_CODES = frozenset({401, 403})


def _is_timeout(error: Exception) -> bool:
    """True for both a bare socket timeout and one wrapped in a URLError.

    ``urlopen`` raises a bare ``TimeoutError`` for some timeout paths and a
    ``URLError`` wrapping one for others, depending on where in the
    connection the timeout occurs.
    """
    if isinstance(error, TimeoutError):
        return True
    return isinstance(error, URLError) and isinstance(error.reason, TimeoutError)


def post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int = 60,
) -> dict[str, Any]:
    """Send a JSON request and normalize transport errors to diagnosable
    ``AIProviderException`` messages -- distinguishing a timeout and an
    authentication failure from a generic transport error, since those are
    the two most common first-time-setup failure modes and need different
    fixes (raise ``ATLAS_AI_TIMEOUT_SECONDS`` vs. fix the API key)."""
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
    except HTTPError as error:
        elapsed = time.monotonic() - started_at
        logger.info("AI request to %s failed after %.1fs: %s", url, elapsed, error)
        if error.code in _AUTH_ERROR_CODES:
            raise AIProviderException(
                f"AI provider rejected the request ({error.code} {error.reason}). "
                "The configured API key is missing, invalid, or lacks access to "
                "this model -- check the *_API_KEY value in your .env against "
                ".env.example, or run 'atlas presentation diagnostics "
                "--project-id <uuid>' to confirm which project/stage is affected."
            ) from error
        raise AIProviderException(
            f"AI protocol request failed ({error.code} {error.reason}): {error}"
        ) from error
    except (URLError, OSError, json.JSONDecodeError) as error:
        elapsed = time.monotonic() - started_at
        logger.info("AI request to %s failed after %.1fs: %s", url, elapsed, error)
        if _is_timeout(error):
            raise AIProviderException(
                f"AI provider request timed out after {timeout}s. If you're "
                "using a locally-hosted model (Ollama, LM Studio), this is "
                "often just slow generation on modest hardware, not a real "
                "failure -- try raising ATLAS_AI_TIMEOUT_SECONDS (e.g. to "
                "180-300) in your .env and retrying."
            ) from error
        raise AIProviderException(f"AI protocol request failed: {error}") from error
    elapsed = time.monotonic() - started_at
    logger.info("AI request to %s completed in %.1fs", url, elapsed)
    if not isinstance(result, dict):
        raise AIProviderException("AI protocol returned a non-object JSON response.")
    return result
