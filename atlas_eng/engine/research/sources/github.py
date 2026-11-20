"""GitHub repository source -- finds existing open-source alternatives.

https://docs.github.com/en/rest/search/search#search-repositories

Works without a token (about 10 searches a minute). Set ``ATLAS_GITHUB_TOKEN``
for a higher limit.
"""

import logging

import httpx

from atlas_eng.engine.research.sources.base import RateLimiter, narrowing_queries
from atlas_eng.engine.research.sources.models import PaperCandidate

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.github.com/search/repositories"
_MIN_INTERVAL_SECONDS = 2.0


class GitHubSource:
    """Searches public repositories by relevance."""

    name = "github"

    def __init__(
        self,
        client: httpx.Client | None = None,
        timeout_seconds: int = 15,
        token: str | None = None,
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._token = token
        self._rate_limiter = RateLimiter(_MIN_INTERVAL_SECONDS)
        self.last_call_failed = False

    def search(self, query: str, max_results: int) -> list[PaperCandidate]:
        self.last_call_failed = False
        for attempt in narrowing_queries(query):
            self._rate_limiter.wait()
            try:
                candidates = self._search_once(attempt, max_results)
            except (httpx.HTTPError, ValueError) as error:
                logger.warning("GitHub search failed for query %r: %s", attempt, error)
                self.last_call_failed = True
                return []
            if candidates:
                return candidates
        return []

    def _search_once(self, query: str, max_results: int) -> list[PaperCandidate]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        response = self._client.get(
            _BASE_URL,
            params={"q": query, "per_page": max_results},
            headers=headers,
        )
        response.raise_for_status()
        candidates = []
        for item in response.json().get("items", []):
            candidate = self._parse_item(item)
            if candidate:
                candidates.append(candidate)
        return candidates

    def _parse_item(self, item: dict[str, object]) -> PaperCandidate | None:
        full_name = item.get("full_name")
        url = item.get("html_url")
        if not isinstance(full_name, str) or not isinstance(url, str):
            return None
        facts = [
            f"{item['stargazers_count']} stars"
            if isinstance(item.get("stargazers_count"), int)
            else "",
            f"last pushed {str(item['pushed_at'])[:10]}"
            if item.get("pushed_at")
            else "",
            str(item["language"]) if item.get("language") else "",
        ]
        description = str(item.get("description") or "No description.")
        abstract = f"{description} ({', '.join(fact for fact in facts if fact)})"
        return PaperCandidate(
            title=full_name,
            authors=[],
            year=None,
            url=url,
            abstract=abstract,
            source=self.name,
            kind="repository",
            external_id=f"github:{full_name}",
        )
