"""Services for managing the Research lifecycle."""

from uuid import UUID

from engine.domain.enums import ResearchStatus
from engine.domain.metadata import ArtifactMetadata
from engine.domain.research import (
    Assumption,
    Constraint,
    Evidence,
    Opportunity,
    ProblemDefinition,
    Research,
    ResearchFinding,
    ResearchSnapshot,
    ResearchSource,
    ResearchSummary,
)
from engine.research.exceptions import (
    InvalidResearchOperationException,
    ResearchNotFoundException,
)
from engine.research.repository import ResearchRepository


class ResearchInitializationService:
    """Handles creating the initial research state for a project."""

    def __init__(self, repository: ResearchRepository) -> None:
        self.repository = repository

    def initialize_research(
        self, project_id: UUID, problem_statement: str, objectives: list[str]
    ) -> Research:
        """Create a new research context for a project."""
        if self.repository.exists(project_id):
            raise InvalidResearchOperationException(
                f"Research already exists for project {project_id}."
            )

        problem = ProblemDefinition(
            statement=problem_statement, objectives=objectives
        )
        research = Research(
            project_id=project_id,
            status=ResearchStatus.DRAFT,
            problem_definition=problem,
        )
        self.repository.save(research)
        return research


class ResearchCaptureService:
    """Handles collecting external information and raw evidence."""

    def __init__(self, repository: ResearchRepository) -> None:
        self.repository = repository

    def _ensure_mutable(self, research: Research) -> None:
        if research.status in (ResearchStatus.APPROVED, ResearchStatus.ARCHIVED):
            raise InvalidResearchOperationException(
                "Cannot mutate research that is APPROVED or ARCHIVED."
            )

    def add_source(
        self, project_id: UUID, title: str, url_or_reference: str
    ) -> ResearchSource:
        """Add an external research source."""
        research = self.repository.get_by_project_id(project_id)
        if not research:
            raise ResearchNotFoundException()
        self._ensure_mutable(research)

        source = ResearchSource(title=title, url_or_reference=url_or_reference)
        research.sources.append(source)
        research.status = ResearchStatus.IN_PROGRESS
        self.repository.save(research)
        return source

    def add_evidence(
        self,
        project_id: UUID,
        type_: str,
        title: str,
        origin: str,
        citation: str,
        summary: str,
        confidence: float = 1.0,
        tags: list[str] | None = None,
        notes: str = "",
    ) -> Evidence:
        """Add a piece of collected evidence."""
        research = self.repository.get_by_project_id(project_id)
        if not research:
            raise ResearchNotFoundException()
        self._ensure_mutable(research)

        evidence = Evidence(
            type=type_,
            title=title,
            origin=origin,
            citation=citation,
            summary=summary,
            confidence=confidence,
            tags=tags or [],
            notes=notes,
        )
        research.evidence.append(evidence)
        research.status = ResearchStatus.IN_PROGRESS
        self.repository.save(research)
        return evidence


class ResearchOrganizationService:
    """Handles synthesizing evidence into findings, constraints, and assumptions."""

    def __init__(self, repository: ResearchRepository) -> None:
        self.repository = repository

    def add_finding(
        self, project_id: UUID, title: str, summary: str, evidence_ids: list[UUID]
    ) -> ResearchFinding:
        """Synthesize a finding from evidence."""
        research = self.repository.get_by_project_id(project_id)
        if not research:
            raise ResearchNotFoundException()
        if not evidence_ids:
            raise InvalidResearchOperationException(
                "Findings must reference at least one Evidence ID."
            )

        valid_evidence_ids = {e.id for e in research.evidence}
        if not all(eid in valid_evidence_ids for eid in evidence_ids):
            raise InvalidResearchOperationException("Unknown evidence ID referenced.")

        finding = ResearchFinding(
            title=title, summary=summary, evidence_ids=evidence_ids
        )
        research.findings.append(finding)
        self.repository.save(research)
        return finding

    def add_constraint(
        self,
        project_id: UUID,
        description: str,
        impact: str,
        finding_ids: list[UUID] | None = None,
    ) -> Constraint:
        """Record a discovered constraint."""
        research = self.repository.get_by_project_id(project_id)
        if not research:
            raise ResearchNotFoundException()

        constraint = Constraint(
            description=description, impact=impact, finding_ids=finding_ids or []
        )
        research.constraints.append(constraint)
        self.repository.save(research)
        return constraint

    def add_assumption(
        self, project_id: UUID, description: str, risk: str
    ) -> Assumption:
        """Record a working assumption."""
        research = self.repository.get_by_project_id(project_id)
        if not research:
            raise ResearchNotFoundException()

        assumption = Assumption(description=description, risk=risk)
        research.assumptions.append(assumption)
        self.repository.save(research)
        return assumption


class OpportunityAnalysisService:
    """Handles deriving engineering value (opportunities) from findings."""

    def __init__(self, repository: ResearchRepository) -> None:
        self.repository = repository

    def add_opportunity(
        self, project_id: UUID, title: str, description: str, finding_ids: list[UUID]
    ) -> Opportunity:
        """Create a new opportunity supported by findings."""
        research = self.repository.get_by_project_id(project_id)
        if not research:
            raise ResearchNotFoundException()
        if not finding_ids:
            raise InvalidResearchOperationException(
                "Opportunities must reference at least one Finding ID."
            )

        valid_finding_ids = {f.id for f in research.findings}
        if not all(fid in valid_finding_ids for fid in finding_ids):
            raise InvalidResearchOperationException("Unknown finding ID referenced.")

        opportunity = Opportunity(
            title=title, description=description, finding_ids=finding_ids
        )
        research.opportunities.append(opportunity)
        self.repository.save(research)
        return opportunity


class ResearchSummaryService:
    """Handles finalizing research and creating immutable snapshots."""

    def __init__(self, repository: ResearchRepository) -> None:
        self.repository = repository

    def freeze_snapshot(
        self,
        project_id: UUID,
        synthesis: str,
        key_takeaways: list[str],
        confidence: float,
    ) -> ResearchSnapshot:
        """Synthesize the current state into an immutable snapshot."""
        research = self.repository.get_by_project_id(project_id)
        if not research:
            raise ResearchNotFoundException()
        if not research.problem_definition:
            raise InvalidResearchOperationException(
                "Cannot freeze snapshot without a problem definition."
            )

        summary = ResearchSummary(
            synthesis=synthesis, key_takeaways=key_takeaways
        )
        next_version = len(research.snapshots) + 1

        snapshot = ResearchSnapshot(
            metadata=ArtifactMetadata(version=next_version),
            problem_definition=research.problem_definition,
            research_sources=list(research.sources),
            evidence=list(research.evidence),
            findings=list(research.findings),
            constraints=list(research.constraints),
            assumptions=list(research.assumptions),
            opportunities=list(research.opportunities),
            open_questions=list(research.open_questions),
            summary=summary,
            confidence=confidence,
        )

        research.snapshots.append(snapshot)
        research.status = ResearchStatus.APPROVED

        self.repository.save(research)
        return snapshot
