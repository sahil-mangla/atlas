"""Offline paper source used with ``ATLAS_AI_PROTOCOL=SCRIPTED``.

Returns fixed, clearly-labelled placeholder papers so the research stage can
run with no network. These are not real publications: every title is marked
as a demo fixture and every URL uses the reserved ``.invalid`` domain, so a
proposal produced offline can never be mistaken for one grounded in real
literature.
"""

from atlas_eng.engine.research.sources.models import PaperCandidate

_FIXTURES = (
    PaperCandidate(
        title="[Demo fixture] Human-in-the-loop review of generated designs",
        authors=["A. Placeholder", "B. Example"],
        year=2024,
        url="https://atlas-demo.invalid/papers/1",
        abstract=(
            "Placeholder abstract used by the offline scripted source. It "
            "describes reviewing generated engineering proposals before "
            "they are committed."
        ),
        source="scripted",
        external_id="scripted:demo-1",
    ),
    PaperCandidate(
        title="[Demo fixture] Traceability in staged engineering workflows",
        authors=["C. Sample"],
        year=2023,
        url="https://atlas-demo.invalid/papers/2",
        abstract=(
            "Placeholder abstract used by the offline scripted source. It "
            "describes linking decisions back to the evidence behind them."
        ),
        source="scripted",
        external_id="scripted:demo-2",
    ),
)


class ScriptedPaperSource:
    """A ``PaperSource`` that needs no network and never fails."""

    name = "scripted"

    def __init__(self) -> None:
        self.last_call_failed = False

    def search(self, _query: str, max_results: int) -> list[PaperCandidate]:
        """Return up to ``max_results`` fixed placeholder candidates."""
        self.last_call_failed = False
        return list(_FIXTURES[:max_results])


_MARKET_FIXTURES = (
    PaperCandidate(
        title="[Demo fixture] example-org/design-review-tool",
        url="https://atlas-demo.invalid/repos/1",
        abstract=(
            "Placeholder repository used by the offline scripted source. It "
            "stands in for an existing open-source alternative "
            "(120 stars, last pushed 2024-01-01)."
        ),
        source="scripted-market",
        kind="repository",
        external_id="scripted-market:demo-1",
    ),
    PaperCandidate(
        title="[Demo fixture] Show HN: a design review assistant",
        year=2024,
        url="https://atlas-demo.invalid/discussions/1",
        abstract=(
            "Placeholder discussion used by the offline scripted source. It "
            "stands in for a launch thread where users describe what current "
            "tools leave out (45 points, 12 comments)."
        ),
        source="scripted-market",
        kind="discussion",
        external_id="scripted-market:demo-2",
    ),
)


class ScriptedMarketSource:
    """A market-research source that needs no network and never fails."""

    name = "scripted-market"

    def __init__(self) -> None:
        self.last_call_failed = False

    def search(self, _query: str, max_results: int) -> list[PaperCandidate]:
        """Return up to ``max_results`` fixed placeholder candidates."""
        self.last_call_failed = False
        return list(_MARKET_FIXTURES[:max_results])
