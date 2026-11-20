"""Hacker News source -- launches and discussions about existing products.

https://hn.algolia.com/api -- free, no key. Surfaces "Show HN" launches and
threads where people describe what current tools get wrong.
"""

import logging

import httpx

from atlas_eng.engine.research.sources.base import RateLimiter, narrowing_queries
from atlas_eng.engine.research.sources.models import PaperCandidate

logger = logging.getLogger(__name__)

_BASE_URL = "https://hn.algolia.com/api/v1/search"
_MIN_INTERVAL_SECONDS = 1.0
_YEAR_CHARS = 4


class HackerNewsSource:
    """Searches Hacker News stories by relevance."""

    name = "hackernews"

    def __init__(
        self, client: httpx.Client | None = None, timeout_seconds: int = 15
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._rate_limiter = RateLimiter(_MIN_INTERVAL_SECONDS)
        self.last_call_failed = False

    def search(self, query: str, max_results: int) -> list[PaperCandidate]:
        self.last_call_failed = False
        for attempt in narrowing_queries(query):
            self._rate_limiter.wait()
            try:
                candidates = self._search_once(attempt, max_results)
            except (httpx.HTTPError, ValueError) as error:
                logger.warning(
                    "Hacker News search failed for query %r: %s", attempt, error
                )
                self.last_call_failed = True
                return []
            if candidates:
                return candidates
        return []

    def _search_once(self, query: str, max_results: int) -> list[PaperCandidate]:
        response = self._client.get(
            _BASE_URL,
            params={"query": query, "tags": "story", "hitsPerPage": max_results},
        )
        response.raise_for_status()
        candidates = []
        for hit in response.json().get("hits", []):
            candidate = self._parse_hit(hit)
            if candidate:
                candidates.append(candidate)
        return candidates

    def _parse_hit(self, hit: dict[str, object]) -> PaperCandidate | None:
        object_id = hit.get("objectID")
        title = hit.get("title")
        if not isinstance(object_id, str) or not isinstance(title, str):
            return None
        created = str(hit.get("created_at") or "")
        year = int(created[:_YEAR_CHARS]) if created[:_YEAR_CHARS].isdigit() else None
        text = str(hit.get("story_text") or "").strip()
        stats = (
            f"{hit.get('points') or 0} points, {hit.get('num_comments') or 0} comments"
        )
        # The discussion thread is the evidence, so link to it, not the article.
        return PaperCandidate(
            title=title,
            authors=[str(hit["author"])] if hit.get("author") else [],
            year=year,
            url=f"https://news.ycombinator.com/item?id={object_id}",
            abstract=f"{text or title} ({stats}).",
            source=self.name,
            kind="discussion",
            external_id=f"hackernews:{object_id}",
        )
