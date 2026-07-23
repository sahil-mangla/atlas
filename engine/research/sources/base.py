"""Protocol shared by all paper-retrieval sources."""

from typing import Protocol

from engine.research.sources.models import PaperCandidate


class PaperSource(Protocol):
    """A source that can be searched for real, citable papers."""

    name: str

    def search(self, query: str, max_results: int) -> list[PaperCandidate]:
        """Return up to ``max_results`` candidates matching ``query``.

        Implementations must never raise on network/API failure -- a single
        unreachable source must not block research generation -- and should
        return an empty list instead, after logging the failure.
        """
        ...
