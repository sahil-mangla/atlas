from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from engine.architecture.exceptions import (
    ArchitectureNotFoundException,
    InvalidArchitectureOperationException,
)
from engine.architecture.fs_repository import FilesystemArchitectureRepository
from engine.architecture.services import (
    ArchitecturalDecisionService,
    ArchitectureCompositionService,
    ArchitectureInitializationService,
    ArchitectureSummaryService,
    ComponentModelService,
    InterfaceContractService,
    RiskAnalysisService,
)
from engine.domain.enums import ArchitectureStatus
from engine.domain.metadata import ArtifactMetadata
from engine.domain.planning import (
    EngineeringDeliverable,
    Planning,
    PlanningEpic,
    PlanningMilestone,
    PlanningSnapshot,
    PlanningSummary,
    PlanningTask,
    ScopeDefinition,
)
from engine.domain.project import Project
from engine.domain.research import (
    Assumption as ResearchAssumption,
)
from engine.domain.research import (
    Constraint as ResearchConstraint,
)
from engine.domain.research import (
    Evidence,
    ProblemDefinition,
    Research,
    ResearchFinding,
    ResearchSnapshot,
    ResearchSummary,
)
from engine.planning.fs_repository import FilesystemPlanningRepository
from engine.project.fs_repository import FilesystemProjectRepository
from engine.research.fs_repository import FilesystemResearchRepository


@pytest.fixture
def setup_context(tmp_path: Path) -> dict[str, Any]:
    project_repo = FilesystemProjectRepository(tmp_path)
    research_repo = FilesystemResearchRepository(project_repo)
    planning_repo = FilesystemPlanningRepository(project_repo)
    architecture_repo = FilesystemArchitectureRepository(project_repo)

    # 1. Save project
    project = Project(name="Architecture Project", description="d", objective="o")
    project_repo.save(project)

    # 2. Setup research with approved snapshot
    research = Research(project_id=project.id)
    research_snapshot_id = uuid4()
    evidence_id = uuid4()
    finding_id = uuid4()
    res_constraint_id = uuid4()
    res_assumption_id = uuid4()

    evidence = Evidence(
        id=evidence_id,
        type="lit",
        title="Ev 1",
        origin="Docs",
        citation="Cit 1",
        summary="Works",
    )
    finding = ResearchFinding(
        id=finding_id,
        title="Find 1",
        summary="Use PostgreSQL",
        evidence_ids=[evidence_id],
    )
    res_constraint = ResearchConstraint(
        id=res_constraint_id,
        description="Limit cost",
        impact="Low budget",
        finding_ids=[finding_id],
    )
    res_assumption = ResearchAssumption(
        id=res_assumption_id,
        description="Docker runs locally",
        risk="Cannot run local setup",
    )

    r_snapshot = ResearchSnapshot(
        metadata=ArtifactMetadata(id=research_snapshot_id, version=1),
        problem_definition=ProblemDefinition(statement="Problem statement", objectives=["Obj 1"]),
        research_sources=[],
        evidence=[evidence],
        findings=[finding],
        constraints=[res_constraint],
        assumptions=[res_assumption],
        opportunities=[],
        open_questions=[],
        summary=ResearchSummary(synthesis="Research synthesized", key_takeaways=["Takeaway 1"]),
        confidence=0.9,
    )
    research.snapshots.append(r_snapshot)
    research_repo.save(research)

    # 3. Setup planning with approved snapshot
    planning = Planning(project_id=project.id)
    planning_snapshot_id = uuid4()
    deliverable_id = uuid4()
    task_id = uuid4()

    deliverable = EngineeringDeliverable(id=deliverable_id, title="Database Schema")
    scope = ScopeDefinition(statement="Planning Scope", deliverables=[deliverable])
    task = PlanningTask(id=task_id, title="Implement PG Schema")
    epic = PlanningEpic(title="DB Epic", tasks=[task])
    milestone = PlanningMilestone(title="M1", epics=[epic])

    p_snapshot = PlanningSnapshot(
        metadata=ArtifactMetadata(id=planning_snapshot_id, version=1),
        research_snapshot_id=research_snapshot_id,
        scope_definition=scope,
        milestones=[milestone],
        summary=PlanningSummary(synthesis="Planning complete", total_milestones=1, total_tasks=1),
    )
    planning.snapshots.append(p_snapshot)
    planning_repo.save(planning)

    return {
        "project_id": project.id,
        "research_snapshot_id": research_snapshot_id,
        "planning_snapshot_id": planning_snapshot_id,
        "evidence_id": evidence_id,
        "finding_id": finding_id,
        "res_constraint_id": res_constraint_id,
        "res_assumption_id": res_assumption_id,
        "deliverable_id": deliverable_id,
        "task_id": task_id,
        "project_repo": project_repo,
        "research_repo": research_repo,
        "planning_repo": planning_repo,
        "architecture_repo": architecture_repo,
    }


def test_initialization_service(setup_context: dict[str, Any]) -> None:
    ctx = setup_context
    init_svc = ArchitectureInitializationService(
        ctx["project_repo"],
        ctx["research_repo"],
        ctx["planning_repo"],
        ctx["architecture_repo"],
    )

    # Success case
    arch = init_svc.initialize_architecture(
        ctx["project_id"],
        ctx["research_snapshot_id"],
        ctx["planning_snapshot_id"],
    )
    assert arch.project_id == ctx["project_id"]
    assert arch.status == ArchitectureStatus.DRAFT
    assert ctx["architecture_repo"].exists(ctx["project_id"]) is True

    # Duplicate initialization raises error
    with pytest.raises(InvalidArchitectureOperationException):
        init_svc.initialize_architecture(
            ctx["project_id"],
            ctx["research_snapshot_id"],
            ctx["planning_snapshot_id"],
        )

    # Nonexistent project raises error
    with pytest.raises(ArchitectureNotFoundException):
        init_svc.initialize_architecture(
            uuid4(),
            ctx["research_snapshot_id"],
            ctx["planning_snapshot_id"],
        )


def test_composition_service(setup_context: dict[str, Any]) -> None:
    ctx = setup_context
    architecture_repo = ctx["architecture_repo"]
    init_svc = ArchitectureInitializationService(
        ctx["project_repo"],
        ctx["research_repo"],
        ctx["planning_repo"],
        architecture_repo,
    )
    init_svc.initialize_architecture(
        ctx["project_id"],
        ctx["research_snapshot_id"],
        ctx["planning_snapshot_id"],
    )

    comp_svc = ArchitectureCompositionService(
        architecture_repo,
        ctx["research_repo"],
        ctx["planning_repo"],
    )

    # Set design summary
    comp_svc.set_design_summary(ctx["project_id"], "Microservices architecture")
    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert arch.design_summary == "Microservices architecture"

    # Add constraints
    c1 = comp_svc.add_constraint(
        ctx["project_id"],
        "Must run in docker",
        "Local deployment constraint",
        ctx["res_constraint_id"],
    )
    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert len(arch.constraints) == 1
    assert arch.constraints[0].description == "Must run in docker"
    assert arch.constraints[0].related_research_constraint_id == ctx["res_constraint_id"]

    # Invalid research constraint ID raises error
    with pytest.raises(InvalidArchitectureOperationException):
        comp_svc.add_constraint(
            ctx["project_id"],
            "C2",
            "Impact 2",
            uuid4(),
        )

    # Add assumptions
    a1 = comp_svc.add_assumption(
        ctx["project_id"],
        "DB is local",
        "No network delay expected",
        ctx["res_assumption_id"],
    )
    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert len(arch.assumptions) == 1
    assert arch.assumptions[0].description == "DB is local"
    assert arch.assumptions[0].related_research_assumption_id == ctx["res_assumption_id"]

    # Invalid research assumption ID raises error
    with pytest.raises(InvalidArchitectureOperationException):
        comp_svc.add_assumption(
            ctx["project_id"],
            "A2",
            "Risk 2",
            uuid4(),
        )

    # Add quality attribute
    comp_svc.add_quality_attribute(
        ctx["project_id"],
        "Scalability",
        "Scale to 10k users",
        "Use Redis cache",
    )
    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert len(arch.quality_attributes) == 1
    assert arch.quality_attributes[0].name == "Scalability"

    # Add driver
    driver = comp_svc.add_architecture_driver(
        ctx["project_id"],
        "Database Choice Driver",
        "Requires reliable SQL",
        "Database Selection",
        [ctx["finding_id"]],
        [ctx["deliverable_id"]],
    )
    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert len(arch.drivers) == 1
    assert arch.drivers[0].name == "Database Choice Driver"
    assert arch.drivers[0].source_finding_ids == [ctx["finding_id"]]
    assert arch.drivers[0].source_objective_ids == [ctx["deliverable_id"]]

    # Invalid source finding raises error
    with pytest.raises(InvalidArchitectureOperationException):
        comp_svc.add_architecture_driver(
            ctx["project_id"],
            "D2",
            "Desc 2",
            "Type 2",
            [uuid4()],
            [],
        )

    # Invalid planning objective raises error
    with pytest.raises(InvalidArchitectureOperationException):
        comp_svc.add_architecture_driver(
            ctx["project_id"],
            "D2",
            "Desc 2",
            "Type 2",
            [],
            [uuid4()],
        )


def test_adr_service(setup_context: dict[str, Any]) -> None:
    ctx = setup_context
    architecture_repo = ctx["architecture_repo"]
    init_svc = ArchitectureInitializationService(
        ctx["project_repo"],
        ctx["research_repo"],
        ctx["planning_repo"],
        architecture_repo,
    )
    init_svc.initialize_architecture(
        ctx["project_id"],
        ctx["research_snapshot_id"],
        ctx["planning_snapshot_id"],
    )

    comp_svc = ArchitectureCompositionService(
        architecture_repo,
        ctx["research_repo"],
        ctx["planning_repo"],
    )
    c1 = comp_svc.add_constraint(ctx["project_id"], "C1", "I1")
    a1 = comp_svc.add_assumption(ctx["project_id"], "A1", "R1")

    adr_svc = ArchitecturalDecisionService(
        architecture_repo,
        ctx["research_repo"],
        ctx["planning_repo"],
    )

    # Add ADR success
    adr = adr_svc.add_adr(
        ctx["project_id"],
        "ADR-1: Use PG",
        "We need reliable SQL",
        "Choose DB",
        "Adopt PostgreSQL",
        "Strong ACID support",
        consequences="None",
        alternatives_considered=["MySQL"],
        reasons_rejected=["MySQL replication is annoying"],
        trade_offs=["Deployment overhead"],
        related_constraints=[c1.id],
        related_assumptions=[a1.id],
        supporting_evidence=[ctx["evidence_id"]],
        related_planning_tasks=[ctx["task_id"]],
        related_research_findings=[ctx["finding_id"]],
        traceability_links=["link1"],
    )

    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert len(arch.decisions) == 1
    assert arch.decisions[0].title == "ADR-1: Use PG"
    assert arch.decisions[0].related_constraints == [c1.id]
    assert arch.decisions[0].related_planning_tasks == [ctx["task_id"]]

    # Invalid local constraint raises error
    with pytest.raises(InvalidArchitectureOperationException):
        adr_svc.add_adr(
            ctx["project_id"],
            "ADR-2",
            "ctx",
            "prob",
            "dec",
            "rat",
            related_constraints=[uuid4()],
        )

    # Invalid local assumption raises error
    with pytest.raises(InvalidArchitectureOperationException):
        adr_svc.add_adr(
            ctx["project_id"],
            "ADR-2",
            "ctx",
            "prob",
            "dec",
            "rat",
            related_assumptions=[uuid4()],
        )

    # Invalid research evidence raises error
    with pytest.raises(InvalidArchitectureOperationException):
        adr_svc.add_adr(
            ctx["project_id"],
            "ADR-2",
            "ctx",
            "prob",
            "dec",
            "rat",
            supporting_evidence=[uuid4()],
        )

    # Invalid research finding raises error
    with pytest.raises(InvalidArchitectureOperationException):
        adr_svc.add_adr(
            ctx["project_id"],
            "ADR-2",
            "ctx",
            "prob",
            "dec",
            "rat",
            related_research_findings=[uuid4()],
        )

    # Invalid planning task raises error
    with pytest.raises(InvalidArchitectureOperationException):
        adr_svc.add_adr(
            ctx["project_id"],
            "ADR-2",
            "ctx",
            "prob",
            "dec",
            "rat",
            related_planning_tasks=[uuid4()],
        )


def test_component_and_interface_service(setup_context: dict[str, Any]) -> None:
    ctx = setup_context
    architecture_repo = ctx["architecture_repo"]
    init_svc = ArchitectureInitializationService(
        ctx["project_repo"],
        ctx["research_repo"],
        ctx["planning_repo"],
        architecture_repo,
    )
    init_svc.initialize_architecture(
        ctx["project_id"],
        ctx["research_snapshot_id"],
        ctx["planning_snapshot_id"],
    )

    comp_svc = ComponentModelService(architecture_repo)
    int_svc = InterfaceContractService(architecture_repo)

    # Add Component
    c1 = comp_svc.add_component(
        ctx["project_id"],
        "Auth Service",
        ["Authenticates users"],
        ["user-db"],
        [],
    )
    c2 = comp_svc.add_component(
        ctx["project_id"],
        "Order Service",
        ["Manages orders"],
        ["order-db"],
        ["Stripe API"],
    )

    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert len(arch.components) == 2
    assert arch.components[0].name == "Auth Service"
    assert arch.components[1].name == "Order Service"
    assert arch.components[1].external_dependencies == ["Stripe API"]

    # Add internal dependency
    comp_svc.add_internal_dependency(ctx["project_id"], c2.id, c1.id)
    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert arch.components[1].internal_dependencies == [c1.id]

    # Try introducing cycle: c1 -> c2 (since c2 already depends on c1, this creates a cycle)
    with pytest.raises(InvalidArchitectureOperationException):
        comp_svc.add_internal_dependency(ctx["project_id"], c1.id, c2.id)

    # Try self-dependency
    with pytest.raises(InvalidArchitectureOperationException):
        comp_svc.add_internal_dependency(ctx["project_id"], c1.id, c1.id)

    # Add interface contract
    contract = int_svc.add_interface_contract(
        ctx["project_id"],
        c1.id,
        "ValidateToken",
        "Verifies JWT",
        "gRPC",
        "TokenRequest",
        "TokenResponse",
    )
    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert len(arch.components[0].public_interfaces) == 1
    assert arch.components[0].public_interfaces[0].name == "ValidateToken"


def test_risk_analysis_service(setup_context: dict[str, Any]) -> None:
    ctx = setup_context
    architecture_repo = ctx["architecture_repo"]
    init_svc = ArchitectureInitializationService(
        ctx["project_repo"],
        ctx["research_repo"],
        ctx["planning_repo"],
        architecture_repo,
    )
    init_svc.initialize_architecture(
        ctx["project_id"],
        ctx["research_snapshot_id"],
        ctx["planning_snapshot_id"],
    )

    adr_svc = ArchitecturalDecisionService(
        architecture_repo,
        ctx["research_repo"],
        ctx["planning_repo"],
    )
    adr = adr_svc.add_adr(ctx["project_id"], "ADR-1", "ctx", "prob", "dec", "rat")

    risk_svc = RiskAnalysisService(architecture_repo)

    # Register Risk
    risk = risk_svc.register_risk(
        ctx["project_id"],
        "Performance latency risk",
        "medium",
        "low",
        "medium",
        "Add cache",
        "infra-team",
        adr.id,
    )
    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert len(arch.risks) == 1
    assert arch.risks[0].description == "Performance latency risk"
    assert arch.risks[0].related_decision_id == adr.id

    # Invalid ADR ID raises error
    with pytest.raises(InvalidArchitectureOperationException):
        risk_svc.register_risk(
            ctx["project_id"],
            "R2",
            "low",
            "low",
            "low",
            "mit",
            "own",
            uuid4(),
        )

    # Test Component Model Service - link ADR & Risk
    comp_svc = ComponentModelService(architecture_repo)
    comp = comp_svc.add_component(ctx["project_id"], "C1", [], [], [])

    comp_svc.associate_adr_to_component(ctx["project_id"], comp.id, adr.id)
    comp_svc.associate_risk_to_component(ctx["project_id"], comp.id, risk.id)

    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert arch.components[0].related_adrs == [adr.id]
    assert arch.components[0].related_risks == [risk.id]


def test_summary_and_snapshot_lifecycle(setup_context: dict[str, Any]) -> None:
    ctx = setup_context
    architecture_repo = ctx["architecture_repo"]
    init_svc = ArchitectureInitializationService(
        ctx["project_repo"],
        ctx["research_repo"],
        ctx["planning_repo"],
        architecture_repo,
    )
    init_svc.initialize_architecture(
        ctx["project_id"],
        ctx["research_snapshot_id"],
        ctx["planning_snapshot_id"],
    )

    comp_svc = ComponentModelService(architecture_repo)
    comp = comp_svc.add_component(ctx["project_id"], "C1", [], [], [])

    adr_svc = ArchitecturalDecisionService(
        architecture_repo,
        ctx["research_repo"],
        ctx["planning_repo"],
    )
    adr = adr_svc.add_adr(ctx["project_id"], "ADR-1", "ctx", "prob", "dec", "rat")

    risk_svc = RiskAnalysisService(architecture_repo)
    risk = risk_svc.register_risk(ctx["project_id"], "R1", "low", "low", "low", "mit", "own")

    summary_svc = ArchitectureSummaryService(
        architecture_repo,
        ctx["research_repo"],
        ctx["planning_repo"],
    )

    # 1. Freezing directly from DRAFT status should fail
    with pytest.raises(InvalidArchitectureOperationException):
        summary_svc.freeze_snapshot(
            ctx["project_id"],
            ctx["planning_snapshot_id"],
            ctx["research_snapshot_id"],
            "Synthesis desc",
        )

    # 2. Submit for review
    arch = summary_svc.submit_for_review(ctx["project_id"])
    assert arch.status == ArchitectureStatus.REVIEW

    # 3. Freezing with invalid baseline snapshot IDs should fail
    with pytest.raises(InvalidArchitectureOperationException):
        summary_svc.freeze_snapshot(
            ctx["project_id"],
            uuid4(),  # Invalid planning snapshot
            ctx["research_snapshot_id"],
            "Synthesis desc",
        )
    with pytest.raises(InvalidArchitectureOperationException):
        summary_svc.freeze_snapshot(
            ctx["project_id"],
            ctx["planning_snapshot_id"],
            uuid4(),  # Invalid research snapshot
            "Synthesis desc",
        )

    # 4. Freeze snapshot success
    snapshot = summary_svc.freeze_snapshot(
        ctx["project_id"],
        ctx["planning_snapshot_id"],
        ctx["research_snapshot_id"],
        "Synthesis desc",
    )

    arch = architecture_repo.get_by_project_id(ctx["project_id"])
    assert arch is not None
    assert arch.status == ArchitectureStatus.APPROVED
    assert len(arch.snapshots) == 1
    assert arch.summary is not None
    assert arch.summary.synthesis == "Synthesis desc"
    assert arch.summary.total_components == 1
    assert arch.summary.total_adrs == 1
    assert arch.summary.total_risks == 1

    # Verify frozen snapshot contents
    assert snapshot.metadata.version == 1
    assert snapshot.planning_snapshot_id == ctx["planning_snapshot_id"]
    assert snapshot.research_snapshot_id == ctx["research_snapshot_id"]
    assert snapshot.summary.total_components == 1
    assert len(snapshot.components) == 1
    assert len(snapshot.decisions) == 1

    # 5. Modifying in APPROVED status should raise error
    with pytest.raises(InvalidArchitectureOperationException):
        comp_svc.add_component(ctx["project_id"], "C2", [], [], [])
