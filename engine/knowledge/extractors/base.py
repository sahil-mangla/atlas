from abc import ABC, abstractmethod
from uuid import UUID

from engine.domain.enums import KnowledgeSourceType
from engine.domain.knowledge import KnowledgeCandidate


class KnowledgeExtractor(ABC):
    """Base interface for extracting engineering knowledge from domain artifacts."""

    @property
    @abstractmethod
    def source_type(self) -> KnowledgeSourceType:
        """The type of source artifact this extractor handles."""

    @abstractmethod
    def extract(self, project_id: UUID, source_id: UUID) -> list[KnowledgeCandidate]:
        """Extract knowledge candidates from the given source artifact.

        Args:
            project_id: The UUID of the project.
            source_id: The UUID of the snapshot to extract from.

        Returns:
            A list of KnowledgeCandidate objects ready for deduplication and review.
        """


class ExtractorRegistry:
    """Registry mapping source types to their corresponding extractors."""

    def __init__(self, *extractors: KnowledgeExtractor) -> None:
        self._registry: dict[KnowledgeSourceType, KnowledgeExtractor] = {
            extractor.source_type: extractor for extractor in extractors
        }

    def extract(self, project_id: UUID, source_type: KnowledgeSourceType, source_id: UUID) -> list[KnowledgeCandidate]:
        """Delegate extraction to the appropriate extractor."""
        extractor = self._registry.get(source_type)
        if not extractor:
            return []
        return extractor.extract(project_id, source_id)
