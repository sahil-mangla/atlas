"""Check whether a cited paper exists, using public scholarly indexes.

A citation counts as **verified** when a paper with a near-identical title is
found and at least one author surname or the year (within one) agrees. A
title found with neither is **misattributed**. **Not found** (most likely
invented) is only reported when every source answered and none had a similar
title; if any source could not be searched (rate limit, outage) the citation
is **unchecked** and can be re-checked later. Sources: Crossref, arXiv,
OpenAlex, Semantic Scholar. A source that rate-limits is skipped for the rest
of the run rather than retried. Answers are cached on disk.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import httpx

TITLE_MATCH = 0.9
# A Retry-After longer than this is a daily quota, not a burst limit.
_QUOTA_RETRY_AFTER_S = 60
_ARXIV_NS = {"a": "http://www.w3.org/2005/Atom"}
_STATUSES = ("verified", "misattributed", "not_found", "unchecked")


class _RateLimitedError(Exception):
    """The source refused service (HTTP 429) after polite retries."""


@dataclass
class Candidate:
    title: str
    authors: list[str]
    year: int | None
    source: str


@dataclass
class Verdict:
    status: str
    title_similarity: float
    matched_title: str = ""
    matched_source: str = ""
    author_overlap: bool = False
    year_close: bool = False
    checked: list[str] = field(default_factory=list)


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", text.lower()).split())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalise(a), normalise(b)).ratio()


def surname(name: str) -> str:
    parts = re.sub(r"[^A-Za-z\s-]", " ", name).split()
    return parts[-1].lower() if parts else ""


class Verifier:
    def __init__(self, cache_path: Path) -> None:
        self._cache_path = cache_path
        self._cache: dict[str, list[dict[str, Any]]] = (
            json.loads(cache_path.read_text(encoding="utf-8"))
            if cache_path.exists()
            else {}
        )
        self._client = httpx.Client(
            timeout=30, headers={"User-Agent": "atlas-eng-citation-eval"}
        )
        self._last_arxiv = 0.0
        self._last_crossref = 0.0
        #: Sources that refused service this run; skipped from then on.
        self.unavailable: set[str] = set()

    def close(self) -> None:
        self._cache_path.write_text(json.dumps(self._cache, indent=1), encoding="utf-8")
        self._client.close()

    def _cached(self, source: str, key: str, fetch: Any) -> list[Candidate] | None:
        """Cached candidates, or ``None`` when the source could not be searched."""
        if key in self._cache:
            return [Candidate(**c) for c in self._cache[key]]
        if source in self.unavailable:
            return None
        try:
            candidates = fetch()
        except _RateLimitedError:
            self.unavailable.add(source)
            return None
        except (httpx.HTTPError, ET.ParseError, ValueError, KeyError):
            return None  # not cached: retried on the next run
        found: list[Candidate] = candidates
        self._cache[key] = [asdict(c) for c in found]
        return found

    def _get(self, url: str, params: dict[str, Any]) -> httpx.Response:
        for attempt in range(3):
            response = self._client.get(url, params=params)
            if response.status_code != httpx.codes.TOO_MANY_REQUESTS:
                response.raise_for_status()
                return response
            retry_after = response.headers.get("retry-after", "")
            if retry_after.isdigit() and int(retry_after) > _QUOTA_RETRY_AFTER_S:
                break  # a daily quota, not a burst limit
            time.sleep(5 * (attempt + 1))
        raise _RateLimitedError(url)

    def _crossref(self, title: str) -> list[Candidate]:
        wait = 1.05 - (time.monotonic() - self._last_crossref)
        if wait > 0:
            time.sleep(wait)  # Crossref's public pool allows one request a second
        self._last_crossref = time.monotonic()
        items = self._get(
            "https://api.crossref.org/works",
            {
                "query.bibliographic": title[:300],
                "rows": 5,
                "select": "title,author,issued",
            },
        ).json()["message"]["items"]
        out = []
        for item in items:
            parts = (item.get("issued") or {}).get("date-parts") or [[None]]
            year = parts[0][0] if parts and parts[0] else None
            out.append(
                Candidate(
                    title=" ".join(item.get("title") or []),
                    authors=[
                        f"{a.get('given', '')} {a.get('family', '')}".strip()
                        for a in item.get("author", [])
                    ],
                    year=year if isinstance(year, int) else None,
                    source="crossref",
                )
            )
        return out

    def _openalex(self, title: str) -> list[Candidate]:
        data = self._get(
            "https://api.openalex.org/works",
            {"search": title[:300], "per-page": 5},
        ).json()
        return [
            Candidate(
                title=w.get("title") or "",
                authors=[
                    a["author"]["display_name"]
                    for a in w.get("authorships", [])
                    if a.get("author")
                ],
                year=w.get("publication_year"),
                source="openalex",
            )
            for w in data.get("results", [])
        ]

    def _arxiv(self, title: str) -> list[Candidate]:
        wait = 3.1 - (time.monotonic() - self._last_arxiv)
        if wait > 0:
            time.sleep(wait)  # arXiv asks for at least 3 s between calls
        self._last_arxiv = time.monotonic()
        words = " AND ".join(
            f"ti:{w}" for w in re.findall(r"[A-Za-z0-9]{3,}", title)[:12]
        )
        feed = ET.fromstring(
            self._get(
                "https://export.arxiv.org/api/query",
                {"search_query": words, "max_results": 5},
            ).text
        )
        out = []
        for entry in feed.findall("a:entry", _ARXIV_NS):
            published = entry.findtext("a:published", "", _ARXIV_NS)
            out.append(
                Candidate(
                    title=" ".join(entry.findtext("a:title", "", _ARXIV_NS).split()),
                    authors=[
                        a.findtext("a:name", "", _ARXIV_NS)
                        for a in entry.findall("a:author", _ARXIV_NS)
                    ],
                    year=int(published[:4]) if published[:4].isdigit() else None,
                    source="arxiv",
                )
            )
        return out

    def _semantic_scholar(self, title: str) -> list[Candidate]:
        data = self._get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            {"query": title[:300], "limit": 5, "fields": "title,year,authors"},
        ).json()
        return [
            Candidate(
                title=p.get("title") or "",
                authors=[a.get("name", "") for a in p.get("authors") or []],
                year=p.get("year"),
                source="semantic_scholar",
            )
            for p in data.get("data") or []
        ]

    def verify(self, title: str, authors: list[str], year: int | None) -> Verdict:
        if not title.strip():
            return Verdict(status="not_found", title_similarity=0.0)
        best = Verdict(status="not_found", title_similarity=0.0)
        cited_surnames = {surname(a) for a in authors if surname(a)}
        skipped = False
        for source, fetch in (
            ("crossref", self._crossref),
            ("arxiv", self._arxiv),
            ("openalex", self._openalex),
            ("semantic_scholar", self._semantic_scholar),
        ):
            candidates = self._cached(
                source, f"{source}:{title.lower()}", lambda f=fetch: f(title)
            )
            if candidates is None:
                skipped = True
                continue
            best.checked.append(source)
            for candidate in candidates:
                score = similarity(title, candidate.title)
                found_surnames = {surname(a) for a in candidate.authors}
                agrees = bool(cited_surnames & found_surnames) or (
                    year is not None
                    and candidate.year is not None
                    and abs(year - candidate.year) <= 1
                )
                best_agrees = best.author_overlap or best.year_close
                # Prefer a title match that also agrees on author or year over
                # a slightly closer title that does not.
                better = score > best.title_similarity or (
                    score >= TITLE_MATCH and agrees and not best_agrees
                )
                if not better:
                    continue
                best = Verdict(
                    status="not_found",
                    title_similarity=round(score, 3),
                    matched_title=candidate.title,
                    matched_source=candidate.source,
                    author_overlap=bool(cited_surnames & found_surnames),
                    year_close=(
                        year is not None
                        and candidate.year is not None
                        and abs(year - candidate.year) <= 1
                    ),
                    checked=best.checked,
                )
            if best.title_similarity >= TITLE_MATCH and (
                best.author_overlap or best.year_close
            ):
                break  # a confirmed match; a look-alike title keeps searching
        if best.title_similarity >= TITLE_MATCH:
            # A citation that gives neither authors nor a year cannot be
            # contradicted, so an exact title match stands.
            best.status = (
                "verified"
                if best.author_overlap or best.year_close or not (authors or year)
                else "misattributed"
            )
        elif skipped:
            best.status = "unchecked"
        return best
