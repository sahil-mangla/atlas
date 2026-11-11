"""Deterministic retrieval-eval corpus built from this repo's own documentation.

Atlas has no committed published-knowledge entries, so each ``##``/``###``
documentation section (>= 200 chars) from the architecture docs and ADR-001..005
becomes one ``PublishedKnowledge``-shaped entry. This is *real text* but not
*real reviewed knowledge*: results measured on it are a proxy, not a production
number. ADR-006 is excluded because it documents the feature under test.
"""

import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from engine.domain.enums import (
    KnowledgeActorType,
    KnowledgeCategory,
    KnowledgeSourceType,
)
from engine.domain.knowledge import (
    KnowledgeActor,
    KnowledgeProvenance,
    PublishedKnowledge,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MIN_SECTION_CHARS = 200
PROJECT_ID = uuid5(NAMESPACE_URL, "atlas-retrieval-eval-project")
_SOURCES = ("docs/architecture/*.md", "docs/decisions/adr-00[1-5]*.md")


def _slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")


def entry_id_for(section_id: str) -> UUID:
    """Stable UUID derived from the human-readable section id."""
    return uuid5(NAMESPACE_URL, section_id)


def _commit_time(path: Path) -> datetime:
    """Real last-commit time of the file; used as ``published_at``."""
    out = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "--", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return datetime.fromtimestamp(int(out or 0), tz=UTC)


def build_corpus() -> tuple[list[PublishedKnowledge], dict[UUID, str]]:
    """Return ``(entries, {entry_uuid: section_id})`` in a stable order."""
    actor = KnowledgeActor(actor_type=KnowledgeActorType.SYSTEM, actor_id="eval")
    entries: list[PublishedKnowledge] = []
    section_ids: dict[UUID, str] = {}
    paths = sorted(p for pattern in _SOURCES for p in REPO_ROOT.glob(pattern))
    for path in paths:
        rel = path.relative_to(REPO_ROOT).as_posix()
        published_at = _commit_time(path)
        seen: dict[str, int] = {}
        for chunk in re.split(r"(?m)^(?=#{2,3} )", path.read_text(encoding="utf-8")):
            heading_match = re.match(r"#{2,3} (.+)", chunk)
            if not heading_match or len(chunk.strip()) < MIN_SECTION_CHARS:
                continue
            title = heading_match.group(1).strip()
            slug = _slug(title)
            seen[slug] = seen.get(slug, 0) + 1
            suffix = "" if seen[slug] == 1 else f"-{seen[slug]}"
            section_id = f"{rel}#{slug}{suffix}"
            uid = entry_id_for(section_id)
            body = chunk.split("\n", 1)[1].strip() if "\n" in chunk else ""
            entries.append(
                PublishedKnowledge(
                    id=uid,
                    project_id=PROJECT_ID,
                    title=title,
                    content=body,
                    category=KnowledgeCategory.DECISION_SUMMARY,
                    tags=[],
                    version=1,
                    provenance=KnowledgeProvenance(
                        source_type=KnowledgeSourceType.HUMAN_SUBMISSION,
                        source_id=uid,
                        extracted_at=published_at,
                        actor=actor,
                    ),
                    author=actor,
                    published_at=published_at,
                    candidate_id=uid,
                    deduplication_fingerprint=section_id,
                )
            )
            section_ids[uid] = section_id
    return entries, section_ids
