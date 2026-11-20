"""Protocol shared by all paper-retrieval sources."""

import threading
import time
from typing import Protocol

from atlas_eng.engine.research.sources.models import PaperCandidate


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


_MARKET_QUERY_WORDS = 5


def shorten_query(query: str, words: int = _MARKET_QUERY_WORDS) -> str:
    """Keep the first few keywords of a research query.

    Paper search tolerates a long keyword list, but product and repository
    search require every word to match, so a long query finds nothing.
    """
    return " ".join(query.split()[:words])


_NARROWING_WIDTHS = (4, 3, 2)


def narrowing_queries(query: str) -> list[str]:
    """Progressively shorter versions of a query, longest first.

    GitHub and Hacker News match every word, so a specific query often finds
    nothing while its first two or three words find plenty. Sources try each
    in turn and keep the first that returns results.
    """
    words = query.split()
    attempts: list[str] = []
    for width in _NARROWING_WIDTHS:
        attempt = " ".join(words[:width])
        if attempt and attempt not in attempts:
            attempts.append(attempt)
    return attempts


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
