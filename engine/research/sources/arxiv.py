"""arXiv paper source -- free API, no authentication required.

https://info.arxiv.org/help/api/user-manual.html
"""

import logging
from xml.etree import ElementTree

import httpx

from engine.research.sources.base import RateLimiter
from engine.research.sources.models import PaperCandidate

logger = logging.getLogger(__name__)

_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_BASE_URL = "https://export.arxiv.org/api/query"
# arXiv's API usage policy requires at least 3 seconds between requests:
# https://info.arxiv.org/help/api/user-manual.html#play-nice
_MIN_INTERVAL_SECONDS = 3.0
_QUERY_SYNTAX_CHARS = str.maketrans({"(": " ", ")": " ", ":": " ", '"': " "})


def _sanitize_query(query: str) -> str:
    """Neutralize arXiv search-query grammar so free text is treated literally.

    arXiv's query parser treats uppercase AND/OR/ANDNOT as boolean
    operators, parentheses as grouping, `field:` as a prefix, and double
    quotes as phrase delimiters. A project description containing ordinary
    punctuation (e.g. "latency: reduce cost (P99)") would otherwise be
    silently reinterpreted as query syntax instead of literal search terms.
    """
    return query.translate(_QUERY_SYNTAX_CHARS).lower()


class ArxivSource:
    """Searches arXiv's Atom API for candidate papers."""

    name = "arxiv"

    def __init__(
        self, client: httpx.Client | None = None, timeout_seconds: int = 15
    ) -> None:
        self._client = client or httpx.Client(
            timeout=timeout_seconds, follow_redirects=True
        )
        self._rate_limiter = RateLimiter(_MIN_INTERVAL_SECONDS)
        self.last_call_failed = False

    def search(self, query: str, max_results: int) -> list[PaperCandidate]:
        self._rate_limiter.wait()
        self.last_call_failed = False
        try:
            response = self._client.get(
                _BASE_URL,
                params={
                    "search_query": f"all:{_sanitize_query(query)}",
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "relevance",
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning("arXiv search failed for query %r: %s", query, error)
            self.last_call_failed = True
            return []

        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError as error:
            logger.warning("arXiv response could not be parsed: %s", error)
            self.last_call_failed = True
            return []

        candidates = []
        for entry in root.findall(f"{_ATOM_NS}entry"):
            candidate = self._parse_entry(entry)
            if candidate:
                candidates.append(candidate)
        return candidates

    def _parse_entry(self, entry: ElementTree.Element) -> PaperCandidate | None:
        title_el = entry.find(f"{_ATOM_NS}title")
        summary_el = entry.find(f"{_ATOM_NS}summary")
        id_el = entry.find(f"{_ATOM_NS}id")
        published_el = entry.find(f"{_ATOM_NS}published")
        if (
            title_el is None
            or title_el.text is None
            or id_el is None
            or id_el.text is None
        ):
            return None

        authors = [
            name_el.text.strip()
            for author_el in entry.findall(f"{_ATOM_NS}author")
            if (name_el := author_el.find(f"{_ATOM_NS}name")) is not None
            and name_el.text
        ]
        year = None
        if published_el is not None and published_el.text:
            try:
                year = int(published_el.text[:4])
            except ValueError:
                logger.warning(
                    "arXiv entry has an unparseable <published> value %r; "
                    "keeping the entry with year=None.",
                    published_el.text,
                )

        return PaperCandidate(
            title=" ".join(title_el.text.split()),
            authors=authors,
            year=year,
            url=id_el.text.strip(),
            abstract=" ".join(summary_el.text.split())
            if summary_el is not None and summary_el.text
            else "",
            source=self.name,
            external_id=id_el.text.strip(),
        )
