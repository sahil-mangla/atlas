import httpx

from engine.research.sources.arxiv import ArxivSource
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
