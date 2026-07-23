"""Grounds research evidence in real, retrieved papers instead of LLM recall.

Citation, origin, and title are built deterministically from a paper
source's own API response (see ``engine.research.sources``) -- never passed
through an LLM -- so they stay traceable to a real, checkable record. The
LLM's only role is condensing an already-real abstract into a summary.
"""

import logging
from typing import Protocol
from uuid import UUID

from engine.ai.executor import PromptExecutor
from engine.domain.ai import ContextPayload
from engine.domain.ai_drafts import EvidenceSummaryBatchDraft, ResearchEvidenceDraft
from engine.project.repository import ProjectRepository
from engine.prompt.templates import EvidenceSummaryPromptTemplate
from engine.research.sources.base import PaperSource
from engine.research.sources.models import PaperCandidate

logger = logging.getLogger(__name__)


class EvidenceRetriever(Protocol):
    """What ``ResearchAIEngineeringService`` actually depends on.

    A structural type -- not the concrete ``ResearchRetrievalService`` --
    so callers (including test doubles) only need to implement
    ``retrieve_evidence``, the same pattern already used for ``PaperSource``.
    """

    def retrieve_evidence(self, project_id: UUID) -> list[ResearchEvidenceDraft]: ...


_ABSTRACT_FALLBACK_CHARS = 280
_MAX_CITED_AUTHORS = 3


def _format_citation(candidate: PaperCandidate) -> str:
    if not candidate.authors:
        author_str = "Unknown Author"
    elif len(candidate.authors) > _MAX_CITED_AUTHORS:
        author_str = ", ".join(candidate.authors[:_MAX_CITED_AUTHORS]) + " et al."
    else:
        author_str = ", ".join(candidate.authors)
    year_str = f" ({candidate.year})" if candidate.year else ""
    return f"{author_str}{year_str}. {candidate.title}. {candidate.url}"


def _dedupe(
    candidates: list[PaperCandidate], max_candidates: int
) -> list[PaperCandidate]:
    seen: set[str] = set()
    deduped = []
    for candidate in candidates:
        if candidate.external_id in seen:
            continue
        seen.add(candidate.external_id)
        deduped.append(candidate)
        if len(deduped) >= max_candidates:
            break
    return deduped


class ResearchRetrievalService:
    """Queries real paper sources and turns the results into grounded evidence."""

    def __init__(
        self,
        sources: list[PaperSource],
        project_repo: ProjectRepository,
        prompt_executor: PromptExecutor,
        max_candidates: int = 5,
    ) -> None:
        self._sources = sources
        self._project_repo = project_repo
        self._prompt_executor = prompt_executor
        self._max_candidates = max_candidates
        self._summary_template = EvidenceSummaryPromptTemplate()

    def _build_query(self, project_id: UUID) -> str:
        project = self._project_repo.get_by_id(project_id)
        if not project:
            return ""
        return " ".join(
            part for part in (project.objective, project.description) if part
        ).strip()

    def _search_all_sources(self, query: str) -> list[PaperCandidate]:
        candidates: list[PaperCandidate] = []
        for source in self._sources:
            candidates.extend(source.search(query, self._max_candidates))
        return candidates

    def _summarize(self, candidates: list[PaperCandidate]) -> list[str]:
        """Condense abstracts via the LLM; fall back to truncation on failure."""
        fallback = [
            (c.abstract[:_ABSTRACT_FALLBACK_CHARS] or c.title) for c in candidates
        ]
        serialized = "\n\n".join(
            f"[{i}] {c.title}\n{c.abstract or '(no abstract available)'}"
            for i, c in enumerate(candidates)
        )
        context = ContextPayload(serialized_context=serialized)
        try:
            batch = self._prompt_executor.execute(
                self._summary_template, context, EvidenceSummaryBatchDraft
            )
        except Exception:
            logger.warning("Evidence summarization failed; using truncated abstracts.")
            return fallback

        if len(batch.summaries) != len(candidates):
            logger.warning(
                "Evidence summarization returned %d summaries for %d candidates; "
                "using truncated abstracts instead.",
                len(batch.summaries),
                len(candidates),
            )
            return fallback
        return batch.summaries

    def retrieve_evidence(self, project_id: UUID) -> list[ResearchEvidenceDraft]:
        """Return real, citable evidence grounded in retrieved papers.

        Returns an empty list (never raises) when no query can be built, no
        source is reachable, or nothing relevant is found -- an empty
        evidence list is preferable to fabricated evidence.
        """
        query = self._build_query(project_id)
        if not query:
            return []

        candidates = _dedupe(self._search_all_sources(query), self._max_candidates)
        if not candidates:
            return []

        summaries = self._summarize(candidates)
        return [
            ResearchEvidenceDraft(
                title=candidate.title,
                type="paper",
                origin=f"{candidate.source}: {candidate.url}",
                citation=_format_citation(candidate),
                summary=summary,
            )
            for candidate, summary in zip(candidates, summaries, strict=True)
        ]
