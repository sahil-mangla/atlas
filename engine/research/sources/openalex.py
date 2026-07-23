"""OpenAlex paper source -- free API, no authentication required.

Restricted to open-access works (``filter=is_oa:true``) since OpenAlex is
used here to find real, checkable full texts, not paywalled metadata.
https://docs.openalex.org/api-entities/works
"""

import logging
from typing import Any

import httpx

from engine.research.sources.models import PaperCandidate

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openalex.org/works"
_SELECT = (
    "id,doi,title,publication_year,authorships,open_access,abstract_inverted_index"
)


class OpenAlexSource:
    """Searches OpenAlex for open-access candidate papers."""

    name = "openalex"

    def __init__(
        self, client: httpx.Client | None = None, timeout_seconds: int = 15
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def search(self, query: str, max_results: int) -> list[PaperCandidate]:
        try:
            response = self._client.get(
                _BASE_URL,
                params={
                    "search": query,
                    "filter": "is_oa:true",
                    "per_page": max_results,
                    "select": _SELECT,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning("OpenAlex search failed for query %r: %s", query, error)
            return []

        try:
            payload = response.json()
        except ValueError as error:
            logger.warning("OpenAlex response could not be parsed: %s", error)
            return []

        candidates = []
        for work in payload.get("results", []):
            candidate = self._parse_work(work)
            if candidate:
                candidates.append(candidate)
        return candidates

    def _parse_work(self, work: dict[str, Any]) -> PaperCandidate | None:
        title = work.get("title")
        work_id = work.get("id")
        oa_url = (work.get("open_access") or {}).get("oa_url")
        if not title or not work_id or not oa_url:
            return None

        authors = [
            authorship.get("author", {}).get("display_name", "")
            for authorship in work.get("authorships") or []
            if authorship.get("author", {}).get("display_name")
        ]

        return PaperCandidate(
            title=title,
            authors=authors,
            year=work.get("publication_year"),
            url=oa_url,
            abstract=_reconstruct_abstract(work.get("abstract_inverted_index")),
            source=self.name,
            external_id=work.get("doi") or work_id,
        )


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """OpenAlex stores abstracts as {word: [positions]}; rebuild plain text."""
    if not inverted_index:
        return ""
    positioned: list[tuple[int, str]] = [
        (pos, word) for word, positions in inverted_index.items() for pos in positions
    ]
    positioned.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned)
