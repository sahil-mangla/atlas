import time

import httpx
import pytest

import atlas_eng.engine.research.sources.semantic_scholar as semantic_scholar_module
from atlas_eng.engine.research.sources.arxiv import ArxivSource
from atlas_eng.engine.research.sources.base import RateLimiter
from atlas_eng.engine.research.sources.brave import BraveSearchSource
from atlas_eng.engine.research.sources.github import GitHubSource
from atlas_eng.engine.research.sources.hackernews import HackerNewsSource
from atlas_eng.engine.research.sources.openalex import (
    OpenAlexSource,
    _reconstruct_abstract,
)
from atlas_eng.engine.research.sources.semantic_scholar import SemanticScholarSource

_ARXIV_ATOM_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1234.5678v1</id>
    <published>2023-05-01T00:00:00Z</published>
    <title>  A Study of   Distributed Systems  </title>
    <summary>  This paper studies distributed systems.  </summary>
    <author><name>Ada Lovelace</name></author>
    <author><name>Alan Turing</name></author>
  </entry>
</feed>
"""


def _client_for(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)


def test_arxiv_source_parses_atom_feed() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, text=_ARXIV_ATOM_RESPONSE)
    )
    source = ArxivSource(client=_client_for(transport))

    results = source.search("distributed systems", max_results=5)

    assert len(results) == 1
    candidate = results[0]
    assert candidate.title == "A Study of Distributed Systems"
    assert candidate.authors == ["Ada Lovelace", "Alan Turing"]
    assert candidate.year == 2023
    assert candidate.url == "http://arxiv.org/abs/1234.5678v1"
    assert candidate.source == "arxiv"
    assert "studies distributed systems" in candidate.abstract


def test_arxiv_source_returns_empty_on_http_error() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(500))
    source = ArxivSource(client=_client_for(transport))

    assert source.search("anything", max_results=5) == []
    assert source.last_call_failed is True


def test_arxiv_source_handles_malformed_published_date() -> None:
    """A single entry with an unparseable <published> value must not crash
    the whole search -- the entry is kept with year=None."""
    response_text = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/9999.0001v1</id>
    <published>not-a-date</published>
    <title>Paper With Bad Date</title>
    <summary>Summary text.</summary>
  </entry>
</feed>
"""
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, text=response_text)
    )
    source = ArxivSource(client=_client_for(transport))

    results = source.search("anything", max_results=5)

    assert len(results) == 1
    assert results[0].year is None
    assert source.last_call_failed is False


def test_arxiv_source_sanitizes_query_operators() -> None:
    """Query text containing arXiv operator syntax must reach the API as
    literal search terms, not be reinterpreted as boolean/field syntax."""
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["search_query"] = dict(request.url.params)["search_query"]
        return httpx.Response(200, text=_ARXIV_ATOM_RESPONSE)

    transport = httpx.MockTransport(handler)
    source = ArxivSource(client=_client_for(transport))

    source.search("latency: reduce cost (P99) AND throughput", max_results=5)

    sent_query = captured["search_query"]
    assert sent_query.startswith("all:")
    sanitized_terms = sent_query.removeprefix("all:")
    assert "(" not in sanitized_terms
    assert ")" not in sanitized_terms
    assert ":" not in sanitized_terms
    assert "AND" not in sanitized_terms


def test_arxiv_source_requests_https_base_url() -> None:
    """arXiv's export host 301-redirects http -> https; the base URL must
    be https directly so every call doesn't depend on redirect-following."""
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["scheme"] = request.url.scheme
        captured["host"] = request.url.host
        return httpx.Response(200, text=_ARXIV_ATOM_RESPONSE)

    transport = httpx.MockTransport(handler)
    source = ArxivSource(client=_client_for(transport))

    source.search("distributed systems", max_results=5)

    assert captured["scheme"] == "https"
    assert captured["host"] == "export.arxiv.org"


def test_arxiv_source_default_client_follows_redirects() -> None:
    """Defensive against arXiv adding another redirect hop in the future --
    a client that doesn't follow redirects makes every arXiv search fail
    silently, since export.arxiv.org 301-redirects http to https."""
    source = ArxivSource()

    assert source._client.follow_redirects is True


def test_semantic_scholar_source_parses_response() -> None:
    payload = {
        "data": [
            {
                "title": "Consensus at Scale",
                "abstract": "We describe a consensus protocol.",
                "year": 2020,
                "authors": [{"name": "Barbara Liskov"}],
                "url": "https://www.semanticscholar.org/paper/abc123",
                "externalIds": {"DOI": "10.1000/xyz"},
            },
            {
                # Missing url -- must be dropped, not raise.
                "title": "Incomplete Record",
                "externalIds": {"DOI": "10.1000/incomplete"},
            },
        ]
    }
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    source = SemanticScholarSource(client=_client_for(transport))

    results = source.search("consensus protocols", max_results=5)

    assert len(results) == 1
    assert results[0].title == "Consensus at Scale"
    assert results[0].external_id == "10.1000/xyz"
    assert results[0].source == "semantic_scholar"


def test_semantic_scholar_source_returns_empty_on_http_error() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(503))
    source = SemanticScholarSource(client=_client_for(transport))

    assert source.search("anything", max_results=5) == []
    assert source.last_call_failed is True


def test_semantic_scholar_source_returns_empty_on_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "atlas_eng.engine.research.sources.semantic_scholar.time.sleep",
        lambda _seconds: None,
    )
    transport = httpx.MockTransport(lambda _request: httpx.Response(429))
    source = SemanticScholarSource(client=_client_for(transport))

    assert source.search("anything", max_results=5) == []
    assert source.last_call_failed is True


def test_semantic_scholar_source_retries_after_rate_limit_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient 429 (often shared across an entire egress IP, not caused
    by this caller) must be retried rather than treated as a hard failure."""
    monkeypatch.setattr(
        "atlas_eng.engine.research.sources.semantic_scholar.time.sleep",
        lambda _seconds: None,
    )
    responses = iter(
        [
            httpx.Response(429),
            httpx.Response(200, json={"data": []}),
        ]
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return next(responses)

    transport = httpx.MockTransport(handler)
    source = SemanticScholarSource(client=_client_for(transport))

    results = source.search("anything", max_results=5)

    assert results == []
    assert source.last_call_failed is False


def test_semantic_scholar_source_gives_up_after_max_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "atlas_eng.engine.research.sources.semantic_scholar.time.sleep",
        lambda _seconds: None,
    )
    call_count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(429)

    transport = httpx.MockTransport(handler)
    source = SemanticScholarSource(client=_client_for(transport))

    assert source.search("anything", max_results=5) == []
    assert source.last_call_failed is True
    assert call_count == 3  # initial attempt + 2 retries


def test_semantic_scholar_retry_delay_prefers_retry_after_header() -> None:
    response = httpx.Response(429, headers={"Retry-After": "5"})
    assert semantic_scholar_module._retry_delay_seconds(response, attempt=0) == 5.0


def test_semantic_scholar_retry_delay_caps_retry_after_header() -> None:
    response = httpx.Response(429, headers={"Retry-After": "9999"})
    assert semantic_scholar_module._retry_delay_seconds(response, attempt=0) == 30.0


def test_semantic_scholar_retry_delay_falls_back_to_backoff() -> None:
    response = httpx.Response(429)
    assert semantic_scholar_module._retry_delay_seconds(response, attempt=0) == 2.0
    assert semantic_scholar_module._retry_delay_seconds(response, attempt=1) == 4.0


def test_sources_rate_limit_consecutive_calls() -> None:
    limiter = RateLimiter(min_interval_seconds=0.05)
    limiter.wait()
    start = time.monotonic()
    limiter.wait()
    elapsed = time.monotonic() - start

    assert elapsed >= 0.04


def test_reconstruct_abstract_from_inverted_index() -> None:
    inverted_index = {"real": [1], "This": [0], "abstract.": [2]}
    assert _reconstruct_abstract(inverted_index) == "This real abstract."


def test_reconstruct_abstract_handles_none() -> None:
    assert _reconstruct_abstract(None) == ""


def test_openalex_source_parses_response() -> None:
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "doi": "10.1000/oa",
                "title": "Open Access Systems Research",
                "publication_year": 2022,
                "authorships": [{"author": {"display_name": "Grace Hopper"}}],
                "open_access": {"oa_url": "https://example.org/paper.pdf"},
                "abstract_inverted_index": {"Systems": [0], "research.": [1]},
            },
            {
                # No open-access URL -- must be dropped.
                "id": "https://openalex.org/W456",
                "title": "Paywalled Work",
            },
        ]
    }
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    source = OpenAlexSource(client=_client_for(transport))

    results = source.search("systems research", max_results=5)

    assert len(results) == 1
    assert results[0].title == "Open Access Systems Research"
    assert results[0].external_id == "10.1000/oa"
    assert results[0].abstract == "Systems research."


def test_openalex_source_returns_empty_on_http_error() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(500))
    source = OpenAlexSource(client=_client_for(transport))

    assert source.search("anything", max_results=5) == []
    assert source.last_call_failed is True


def test_openalex_source_handles_explicit_null_author() -> None:
    """A real OpenAlex authorship can have "author": null (anonymized or
    withdrawn authorship) -- must be skipped, not crash with AttributeError."""
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W789",
                "doi": "10.1000/anon",
                "title": "Anonymized Authorship Work",
                "publication_year": 2021,
                "authorships": [
                    {"author": None},
                    {"author": {"display_name": "Known Author"}},
                ],
                "open_access": {"oa_url": "https://example.org/anon.pdf"},
                "abstract_inverted_index": None,
            }
        ]
    }
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    source = OpenAlexSource(client=_client_for(transport))

    results = source.search("anything", max_results=5)

    assert len(results) == 1
    assert results[0].authors == ["Known Author"]
    assert source.last_call_failed is False


def test_github_source_parses_repositories_and_sends_token() -> None:
    seen: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = request
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "full_name": "example/rental-app",
                        "html_url": "https://github.com/example/rental-app",
                        "description": "Rent camera gear.",
                        "stargazers_count": 900,
                        "pushed_at": "2026-03-04T10:00:00Z",
                        "language": "Python",
                    },
                    {"full_name": "broken/entry"},
                ]
            },
        )

    source = GitHubSource(
        client=_client_for(httpx.MockTransport(handler)), token="secret"
    )

    results = source.search("camera rental marketplace photographers owners fleet", 5)

    assert len(results) == 1
    assert results[0].kind == "repository"
    assert results[0].external_id == "github:example/rental-app"
    assert results[0].abstract == (
        "Rent camera gear. (900 stars, last pushed 2026-03-04, Python)"
    )
    request = seen["request"]
    assert request.headers["Authorization"] == "Bearer secret"
    # Repository search needs every word to match, so the query is shortened.
    assert request.url.params["q"] == "camera rental marketplace photographers"


def test_github_source_narrows_the_query_until_something_matches() -> None:
    queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        queries.append(request.url.params["q"])
        items = (
            [{"full_name": "a/b", "html_url": "https://github.com/a/b"}]
            if len(queries[-1].split()) == 2
            else []
        )
        return httpx.Response(200, json={"items": items})

    source = GitHubSource(client=_client_for(httpx.MockTransport(handler)))

    results = source.search("camera rental marketplace photographers owners", 5)

    assert [r.title for r in results] == ["a/b"]
    assert queries == [
        "camera rental marketplace photographers",
        "camera rental marketplace",
        "camera rental",
    ]
    assert source.last_call_failed is False


def test_github_source_returns_empty_on_rate_limit() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(403))
    source = GitHubSource(client=_client_for(transport))

    assert source.search("anything", max_results=5) == []
    assert source.last_call_failed is True


def test_hackernews_source_links_to_the_discussion() -> None:
    payload = {
        "hits": [
            {
                "objectID": "123",
                "title": "Show HN: Camera rental for photographers",
                "url": "https://example.com/launch",
                "author": "founder",
                "points": 88,
                "num_comments": 31,
                "created_at": "2025-06-01T08:00:00.000Z",
                "story_text": None,
            },
            {"objectID": "456"},
        ]
    }
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    source = HackerNewsSource(client=_client_for(transport))

    results = source.search("camera rental", max_results=5)

    assert len(results) == 1
    assert results[0].kind == "discussion"
    assert results[0].url == "https://news.ycombinator.com/item?id=123"
    assert results[0].year == 2025
    assert results[0].authors == ["founder"]
    assert results[0].abstract.endswith("(88 points, 31 comments).")


def test_hackernews_source_returns_empty_on_bad_json() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, text="oops"))
    source = HackerNewsSource(client=_client_for(transport))

    assert source.search("anything", max_results=5) == []
    assert source.last_call_failed is True


def test_brave_source_searches_for_competitors_and_strips_markup() -> None:
    seen: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = request
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "<strong>LensRentals</strong> &amp; more",
                            "url": "https://lensrentals.example/",
                            "description": "Rent <strong>cameras</strong> online.",
                        },
                        {"title": "No url"},
                    ]
                }
            },
        )

    source = BraveSearchSource("key", client=_client_for(httpx.MockTransport(handler)))

    results = source.search("camera rental", max_results=5)

    assert len(results) == 1
    assert results[0].title == "LensRentals & more"
    assert results[0].abstract == "Rent cameras online."
    assert results[0].kind == "web page"
    assert results[0].external_id == "https://lensrentals.example/"
    assert seen["request"].headers["X-Subscription-Token"] == "key"
    assert seen["request"].url.params["q"] == "camera rental alternatives competitors"


def test_brave_source_returns_empty_on_http_error() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(401))
    source = BraveSearchSource("bad", client=_client_for(transport))

    assert source.search("anything", max_results=5) == []
    assert source.last_call_failed is True
