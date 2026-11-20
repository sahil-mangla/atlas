from atlas_eng.engine.research.sources.arxiv import ArxivSource
from atlas_eng.engine.research.sources.base import PaperSource
from atlas_eng.engine.research.sources.brave import BraveSearchSource
from atlas_eng.engine.research.sources.github import GitHubSource
from atlas_eng.engine.research.sources.hackernews import HackerNewsSource
from atlas_eng.engine.research.sources.models import PaperCandidate
from atlas_eng.engine.research.sources.openalex import OpenAlexSource
from atlas_eng.engine.research.sources.semantic_scholar import SemanticScholarSource

__all__ = [
    "ArxivSource",
    "BraveSearchSource",
    "GitHubSource",
    "HackerNewsSource",
    "OpenAlexSource",
    "PaperCandidate",
    "PaperSource",
    "SemanticScholarSource",
]
