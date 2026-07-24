import time

import httpx

from engine.research.sources.arxiv import ArxivSource
from engine.research.sources.base import RateLimiter
from engine.research.sources.openalex import OpenAlexSource, _reconstruct_abstract
from engine.research.sources.semantic_scholar import SemanticScholarSource

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


def test_semantic_scholar_source_returns_empty_on_rate_limit() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(429))
    source = SemanticScholarSource(client=_client_for(transport))

    assert source.search("anything", max_results=5) == []
    assert source.last_call_failed is True


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
