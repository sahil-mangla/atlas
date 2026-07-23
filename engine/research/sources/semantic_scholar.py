"""Semantic Scholar paper source -- free API, no authentication required.

https://api.semanticscholar.org/api-docs/graph
"""

import logging
from typing import Any

import httpx

from engine.research.sources.models import PaperCandidate

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,abstract,year,authors,url,externalIds"


class SemanticScholarSource:
    """Searches Semantic Scholar's structured API for candidate papers."""

    name = "semantic_scholar"

    def __init__(
        self, client: httpx.Client | None = None, timeout_seconds: int = 15
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def search(self, query: str, max_results: int) -> list[PaperCandidate]:
        try:
            response = self._client.get(
                _BASE_URL,
                params={"query": query, "limit": max_results, "fields": _FIELDS},
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning(
                "Semantic Scholar search failed for query %r: %s", query, error
            )
            return []

        try:
            payload = response.json()
        except ValueError as error:
            logger.warning("Semantic Scholar response could not be parsed: %s", error)
            return []

        candidates = []
        for paper in payload.get("data", []):
            candidate = self._parse_paper(paper)
            if candidate:
                candidates.append(candidate)
        return candidates

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
