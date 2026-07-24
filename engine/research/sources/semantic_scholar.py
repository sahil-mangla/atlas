"""Semantic Scholar paper source -- free API, no authentication required.

https://api.semanticscholar.org/api-docs/graph
"""

import logging
import time
from typing import Any

import httpx

from engine.research.sources.base import RateLimiter
from engine.research.sources.models import PaperCandidate

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,abstract,year,authors,url,externalIds"
# Unauthenticated Semantic Scholar allows roughly 100 requests per 5 minutes;
# 3s between requests stays comfortably inside that. In practice this limit
# is often shared across an entire egress IP (e.g. a datacenter or shared
# network), so a single well-behaved caller can still be rate-limited by
# other traffic on the same IP -- hence the retry below rather than treating
# every 429 as a hard failure.
_MIN_INTERVAL_SECONDS = 3.0
_MAX_RETRIES = 2
_RETRY_BACKOFF_SECONDS = 2.0
_MAX_RETRY_AFTER_SECONDS = 30.0


def _retry_delay_seconds(response: httpx.Response, attempt: int) -> float:
    """How long to wait before retrying a 429, in seconds.

    Prefers the server's own ``Retry-After`` header (seconds only -- the
    HTTP-date form is rare from this API and not worth parsing here) over a
    fixed exponential backoff, capped so one retry can't stall a stage for
    an unreasonable amount of time.
    """
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return min(float(retry_after), _MAX_RETRY_AFTER_SECONDS)
        except ValueError:
            pass
    return float(_RETRY_BACKOFF_SECONDS * (2**attempt))


class SemanticScholarSource:
    """Searches Semantic Scholar's structured API for candidate papers."""

    name = "semantic_scholar"

    def __init__(
        self, client: httpx.Client | None = None, timeout_seconds: int = 15
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._rate_limiter = RateLimiter(_MIN_INTERVAL_SECONDS)
        self.last_call_failed = False

    def search(self, query: str, max_results: int) -> list[PaperCandidate]:
        self._rate_limiter.wait()
        self.last_call_failed = False
        try:
            response = self._get_with_retry(query, max_results)
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning(
                "Semantic Scholar search failed for query %r: %s", query, error
            )
            self.last_call_failed = True
            return []

        try:
            payload = response.json()
        except ValueError as error:
            logger.warning("Semantic Scholar response could not be parsed: %s", error)
            self.last_call_failed = True
            return []

        candidates = []
        for paper in payload.get("data", []):
            candidate = self._parse_paper(paper)
            if candidate:
                candidates.append(candidate)
        return candidates

    def _get_with_retry(self, query: str, max_results: int) -> httpx.Response:
        """GET the search endpoint, retrying on 429 with backoff.

        A single 429 doesn't necessarily mean this caller exceeded its own
        rate limit -- unauthenticated Semantic Scholar's limit is often
        shared across an entire egress IP -- so a short wait-and-retry can
        recover a transient throttle instead of returning empty evidence.
        """
        params: dict[str, str | int] = {
            "query": query,
            "limit": max_results,
            "fields": _FIELDS,
        }
        response = self._client.get(_BASE_URL, params=params)
        for attempt in range(_MAX_RETRIES):
            if response.status_code != httpx.codes.TOO_MANY_REQUESTS:
                break
            delay = _retry_delay_seconds(response, attempt)
            logger.warning(
                "Semantic Scholar rate-limited (429) for query %r; "
                "retrying in %.1fs (attempt %d/%d)",
                query,
                delay,
                attempt + 1,
                _MAX_RETRIES,
            )
            time.sleep(delay)
            response = self._client.get(_BASE_URL, params=params)
        return response

    def _parse_paper(self, paper: dict[str, Any]) -> PaperCandidate | None:
        title = paper.get("title")
        external_ids = paper.get("externalIds") or {}
        external_id = external_ids.get("DOI") or paper.get("paperId")
        url = paper.get("url")
        if not title or not external_id or not url:
            return None

        return PaperCandidate(
            title=title,
            authors=[
                a.get("name", "") for a in paper.get("authors") or [] if a.get("name")
            ],
            year=paper.get("year"),
            url=url,
            abstract=paper.get("abstract") or "",
            source=self.name,
            external_id=str(external_id),
        )
