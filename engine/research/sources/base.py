"""Protocol shared by all paper-retrieval sources."""

import threading
import time
from typing import Protocol

from engine.research.sources.models import PaperCandidate


class PaperSource(Protocol):
    """A source that can be searched for real, citable papers."""

    name: str
    last_call_failed: bool

    def search(self, query: str, max_results: int) -> list[PaperCandidate]:
        """Return up to ``max_results`` candidates matching ``query``.

        Implementations must never raise on network/API failure -- a single
        unreachable source must not block research generation -- and should
        return an empty list instead, after logging the failure.

        Must set ``self.last_call_failed`` to reflect whether this call
        actually failed (network/parse error) versus genuinely finding
        nothing, so callers can distinguish an outage from a real empty
        result.
        """
        ...


class RateLimiter:
    """Blocks until at least ``min_interval_seconds`` has passed since the
    last call, so a source doesn't exceed its provider's request-rate policy
    (e.g. arXiv requires >=3s between requests).

    Thread-safe: a source instance may be shared across concurrent
    ``search()`` calls when sources are queried in parallel.
    """

    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval_seconds = min_interval_seconds
        self._lock = threading.Lock()
        self._last_call_time: float | None = None

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            if self._last_call_time is not None:
                elapsed = now - self._last_call_time
                remaining = self._min_interval_seconds - elapsed
                if remaining > 0:
                    time.sleep(remaining)
            self._last_call_time = time.monotonic()
