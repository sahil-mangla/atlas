"""Unit tests for the Research subsystem services.

S-03: FilesystemResearchRepository now requires a registered project. Each
test creates a project in the project repo before operating on research.
"""

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from engine.domain.enums import ResearchStatus
from engine.domain.project import Project
from engine.project.fs_repository import FilesystemProjectRepository
from engine.research.exceptions import (
    InvalidResearchOperationException,
)
from engine.research.fs_repository import FilesystemResearchRepository
from engine.research.services import (
    OpportunityAnalysisService,
    ResearchCaptureService,
    ResearchInitializationService,
    ResearchOrganizationService,
    ResearchSummaryService,
)


@pytest.fixture
def setup(tmp_path: Path) -> tuple[FilesystemResearchRepository, UUID]:
    """Provide a repo and a registered project ID for service tests."""
    project_repo = FilesystemProjectRepository(tmp_path)
    repo = FilesystemResearchRepository(project_repo)

    project = Project(name="Research Test Project", description="d", objective="o")
    project_repo.save(project)

    return repo, project.id


def test_initialization_service(
    setup: tuple[FilesystemResearchRepository, UUID],
) -> None:
    repo, project_id = setup
    svc = ResearchInitializationService(repo)

    research = svc.initialize_research(project_id, "Problem", ["Obj 1"])

    assert research.project_id == project_id
    assert research.status == ResearchStatus.DRAFT
    assert research.problem_definition is not None
    assert research.problem_definition.statement == "Problem"

    with pytest.raises(InvalidResearchOperationException):
        svc.initialize_research(project_id, "Another", [])


def test_capture_service(
    setup: tuple[FilesystemResearchRepository, UUID],
) -> None:
    repo, project_id = setup
    init_svc = ResearchInitializationService(repo)
    cap_svc = ResearchCaptureService(repo)
    init_svc.initialize_research(project_id, "Problem", [])

    source = cap_svc.add_source(project_id, "Docs", "http://docs")
    assert source.title == "Docs"

    evidence = cap_svc.add_evidence(
        project_id, "lit", "Works", "Docs", "Ref 1", "Summary"
    )
    assert evidence.title == "Works"

    research = repo.get_by_project_id(project_id)
    assert research is not None
    assert len(research.sources) == 1
    assert len(research.evidence) == 1


def test_organization_service(
    setup: tuple[FilesystemResearchRepository, UUID],
) -> None:
    repo, project_id = setup
    init_svc = ResearchInitializationService(repo)
    cap_svc = ResearchCaptureService(repo)
    org_svc = ResearchOrganizationService(repo)

    init_svc.initialize_research(project_id, "Problem", [])
    evidence = cap_svc.add_evidence(
        project_id, "lit", "Works", "Docs", "Ref 1", "Summary"
    )

    finding = org_svc.add_finding(project_id, "Finding 1", "Good", [evidence.id])
    assert finding.evidence_ids == [evidence.id]

    with pytest.raises(InvalidResearchOperationException):
        org_svc.add_finding(project_id, "Finding 2", "Bad", [uuid4()])

    constraint = org_svc.add_constraint(
        project_id, "Must be fast", "High", [finding.id]
    )
    assert constraint.finding_ids == [finding.id]

    assumption = org_svc.add_assumption(project_id, "Data is clean", "Low")
    assert assumption.risk == "Low"


def test_opportunity_service(
    setup: tuple[FilesystemResearchRepository, UUID],
) -> None:
    repo, project_id = setup
    init_svc = ResearchInitializationService(repo)
    cap_svc = ResearchCaptureService(repo)
    org_svc = ResearchOrganizationService(repo)
    opp_svc = OpportunityAnalysisService(repo)

    init_svc.initialize_research(project_id, "Problem", [])
    evidence = cap_svc.add_evidence(
        project_id, "lit", "Works", "Docs", "Ref 1", "Summary"
    )
    finding = org_svc.add_finding(project_id, "Finding 1", "Good", [evidence.id])

    opp = opp_svc.add_opportunity(project_id, "Use cache", "Faster", [finding.id])
    assert opp.finding_ids == [finding.id]

    with pytest.raises(InvalidResearchOperationException):
        opp_svc.add_opportunity(project_id, "Bad", "Desc", [uuid4()])


def test_summary_service(
    setup: tuple[FilesystemResearchRepository, UUID],
) -> None:
    repo, project_id = setup
    init_svc = ResearchInitializationService(repo)
    cap_svc = ResearchCaptureService(repo)
    sum_svc = ResearchSummaryService(repo)

    init_svc.initialize_research(project_id, "Problem", [])
    cap_svc.add_evidence(project_id, "lit", "Works", "Docs", "Ref 1", "Summary")

    snapshot = sum_svc.freeze_snapshot(
        project_id, synthesis="Synth", key_takeaways=["TK1"], confidence=0.95
    )
    assert snapshot.metadata.version == 1
    assert snapshot.confidence == 0.95
    assert len(snapshot.evidence) == 1

    research = repo.get_by_project_id(project_id)
    assert research is not None
    assert research.status == ResearchStatus.APPROVED
    assert len(research.snapshots) == 1

    # Active drafts should remain
    assert len(research.evidence) == 1
