"""Brave Search source -- finds commercial competitors and product pages.

https://api-dashboard.search.brave.com/ -- needs an API key
(``ATLAS_BRAVE_API_KEY``), so it only runs when one is configured.
"""

import html
import logging
import re

import httpx

from atlas_eng.engine.research.sources.base import RateLimiter, shorten_query
from atlas_eng.engine.research.sources.models import PaperCandidate

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.search.brave.com/res/v1/web/search"
_MIN_INTERVAL_SECONDS = 1.0
_TAGS = re.compile(r"<[^>]+>")


def _plain(text: str) -> str:
    return " ".join(html.unescape(_TAGS.sub("", text)).split())


class BraveSearchSource:
    """Searches the web for existing products that solve the same problem."""

    name = "brave"

    def __init__(
        self,
        api_key: str,
        client: httpx.Client | None = None,
        timeout_seconds: int = 15,
    ) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._rate_limiter = RateLimiter(_MIN_INTERVAL_SECONDS)
        self.last_call_failed = False

    def search(self, query: str, max_results: int) -> list[PaperCandidate]:
        self._rate_limiter.wait()
        self.last_call_failed = False
        try:
            response = self._client.get(
                _BASE_URL,
                params={
                    "q": f"{shorten_query(query)} alternatives competitors",
                    "count": max_results,
                },
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self._api_key,
                },
            )
            response.raise_for_status()
            results = (response.json().get("web") or {}).get("results", [])
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("Brave search failed for query %r: %s", query, error)
            self.last_call_failed = True
            return []

        candidates = []
        for result in results:
            title, url = result.get("title"), result.get("url")
            if not isinstance(title, str) or not isinstance(url, str):
                continue
            candidates.append(
                PaperCandidate(
                    title=_plain(title),
                    url=url,
                    abstract=_plain(str(result.get("description") or "")),
                    source=self.name,
                    kind="web page",
                    external_id=url,
                )
            )
        return candidates
