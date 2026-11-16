"""Normalized representation of a paper returned by any retrieval source."""

from pydantic import BaseModel, Field


class PaperCandidate(BaseModel):
    """A real, sourced paper found by a retrieval source.

    Every field here is taken directly from the source's API response --
    never invented by an LLM -- so that ``citation``/``origin`` built from it
    are traceable to a real, checkable record.
    """

    title: str = Field(description="Paper title as published.")
    authors: list[str] = Field(default_factory=list, description="Author names.")
    year: int | None = Field(default=None, description="Publication year, if known.")
    url: str = Field(description="Canonical URL for the paper or its landing page.")
    abstract: str = Field(default="", description="Abstract or summary text.")
    source: str = Field(description="Name of the retrieval source, e.g. 'arxiv'.")
    external_id: str = Field(
        description="Source-specific identifier (arXiv ID, DOI, OpenAlex ID) "
        "used to deduplicate candidates found by multiple sources."
    )
