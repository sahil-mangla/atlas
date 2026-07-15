from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from engine.architecture.fs_repository import FilesystemArchitectureRepository
from engine.domain.architecture import (
    ArchitecturalDecision,
    Architecture,
    ArchitectureComponent,
    ArchitectureDriver,
    ArchitectureSnapshot,
    ArchitectureSummary,
    QualityAttribute,
)
from engine.domain.architecture import (
    Constraint as ArchitectureConstraint,
)
from engine.domain.architecture import (
    Risk as ArchitectureRisk,
)
from engine.domain.metadata import ArtifactMetadata, ArtifactStatus
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
from engine.evaluation.exceptions import (
    EvaluationNotFoundException,
    InvalidEvaluationOperationException,
)
from engine.evaluation.fs_repository import FilesystemEvaluationRepository
from engine.evaluation.services import (
    ArchitectureEvaluationService,
    EvaluationInitializationService,
    EvaluationSummaryService,
    QualityEvaluationService,
    ReadinessEvaluationService,
    RequirementCoverageService,
    RiskEvaluationService,
    TraceabilityEvaluationService,
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
    evaluation_repo = FilesystemEvaluationRepository(project_repo)

    # 1. Project
    project = Project(name="Eval Project", description="d", objective="o")
    project_repo.save(project)

    # 2. Research Snapshot
    research = Research(project_id=project.id)
    res_snap_id = uuid4()
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
        summary="Summary Ev",
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
        description="Docker runs",
        risk="Cannot run local setup",
    )

    r_snap = ResearchSnapshot(
        metadata=ArtifactMetadata(id=res_snap_id, version=1),
        problem_definition=ProblemDefinition(
            statement="Problem statement", objectives=["Obj 1"]
        ),
        research_sources=[],
        evidence=[evidence],
        findings=[finding],
        constraints=[res_constraint],
        assumptions=[res_assumption],
        opportunities=[],
        open_questions=[],
        summary=ResearchSummary(
            synthesis="Research synthesized", key_takeaways=["Takeaway 1"]
        ),
        confidence=0.9,
    )
    research.snapshots.append(r_snap)
    research_repo.save(research)

    # 3. Planning Snapshot
    planning = Planning(project_id=project.id)
    plan_snap_id = uuid4()
    deliverable_id = uuid4()
    task_id = uuid4()

    deliverable = EngineeringDeliverable(id=deliverable_id, title="DB Schema")
    scope = ScopeDefinition(statement="Planning Scope", deliverables=[deliverable])
    task = PlanningTask(id=task_id, title="Implement Schema")
    epic = PlanningEpic(title="DB Epic", tasks=[task])
    milestone = PlanningMilestone(title="M1", epics=[epic])

    p_snap = PlanningSnapshot(
        metadata=ArtifactMetadata(id=plan_snap_id, version=1),
        research_snapshot_id=res_snap_id,
        scope_definition=scope,
        milestones=[milestone],
        summary=PlanningSummary(
            synthesis="Planning complete", total_milestones=1, total_tasks=1
        ),
    )
    planning.snapshots.append(p_snap)
    planning_repo.save(planning)

    # 4. Architecture Snapshot
    architecture = Architecture(project_id=project.id)
    arch_snap_id = uuid4()
    arch_constraint_id = uuid4()
    adr_id = uuid4()
    comp_id = uuid4()
    risk_id = uuid4()
    qa_id = uuid4()

    arch_constraint = ArchitectureConstraint(
        id=arch_constraint_id,
        description="Limit cost locally",
        impact="Low budget locally",
        related_research_constraint_id=res_constraint_id,
    )

    # Mapped Driver
    driver = ArchitectureDriver(
        name="DB Selection Driver",
        description="Required to resolve SQL schema",
        driver_type="deliverable",
        source_objective_ids=[deliverable_id],
        target_adr_ids=[adr_id],
    )

    adr = ArchitecturalDecision(
        id=adr_id,
        title="ADR-1: PG",
        context="SQL DB",
        problem_statement="Choose sql",
        decision="Adopt PG",
        rationale="reliable",
        supporting_evidence=[evidence_id],
        related_planning_tasks=[task_id],
        related_research_findings=[finding_id],
        related_constraints=[arch_constraint_id],
    )

    comp = ArchitectureComponent(
        id=comp_id,
        name="DB Component",
        responsibilities=["Store orders"],
        owned_data=["order-db"],
        related_adrs=[adr_id],
        related_risks=[risk_id],
    )

    risk = ArchitectureRisk(
        id=risk_id,
        description="DB failure",
        severity="high",
        likelihood="low",
        impact="high",
        mitigation="backups",
        owner="admin",
        related_decision_id=adr_id,
    )

    qa = QualityAttribute(
        id=qa_id,
        name="Reliability",
        description="Data persistence",
        mitigation_strategy="RAID setup",
        related_adrs=[adr_id],
    )

    a_snap = ArchitectureSnapshot(
        metadata=ArtifactMetadata(id=arch_snap_id, version=1),
        planning_snapshot_id=plan_snap_id,
        research_snapshot_id=res_snap_id,
        drivers=[driver],
        components=[comp],
        decisions=[adr],
        risks=[risk],
        constraints=[arch_constraint],
        assumptions=[],
        quality_attributes=[qa],
        summary=ArchitectureSummary(
            synthesis="Synth", total_components=1, total_adrs=1, total_risks=1
        ),
    )
    architecture.drivers.append(driver)
    architecture.snapshots.append(a_snap)
    architecture_repo.save(architecture)

    return {
        "project_id": project.id,
        "res_snap_id": res_snap_id,
        "plan_snap_id": plan_snap_id,
        "arch_snap_id": arch_snap_id,
        "evidence_id": evidence_id,
        "finding_id": finding_id,
        "res_constraint_id": res_constraint_id,
        "deliverable_id": deliverable_id,
        "task_id": task_id,
        "adr_id": adr_id,
        "comp_id": comp_id,
        "risk_id": risk_id,
        "qa_id": qa_id,
        "project_repo": project_repo,
        "research_repo": research_repo,
        "planning_repo": planning_repo,
        "architecture_repo": architecture_repo,
        "evaluation_repo": evaluation_repo,
    }


def test_initialization_service(setup_context: dict[str, Any]) -> None:
    ctx = setup_context
    init_svc = EvaluationInitializationService(
        ctx["project_repo"],
        ctx["research_repo"],
        ctx["planning_repo"],
        ctx["architecture_repo"],
        ctx["evaluation_repo"],
    )

    # Success case
    eval_obj = init_svc.initialize_evaluation(
        ctx["project_id"],
        ctx["res_snap_id"],
        ctx["plan_snap_id"],
        ctx["arch_snap_id"],
    )
    assert eval_obj.project_id == ctx["project_id"]
    assert eval_obj.status == ArtifactStatus.DRAFT
    assert ctx["evaluation_repo"].exists(ctx["project_id"]) is True

    # Duplicate initialization raises error
    with pytest.raises(InvalidEvaluationOperationException):
        init_svc.initialize_evaluation(
            ctx["project_id"],
            ctx["res_snap_id"],
            ctx["plan_snap_id"],
            ctx["arch_snap_id"],
        )

    # Nonexistent project raises error
    with pytest.raises(EvaluationNotFoundException):
        init_svc.initialize_evaluation(
            uuid4(),
            ctx["res_snap_id"],
            ctx["plan_snap_id"],
            ctx["arch_snap_id"],
        )


def test_evaluation_subservices(setup_context: dict[str, Any]) -> None:
    ctx = setup_context
    evaluation_repo = ctx["evaluation_repo"]
    init_svc = EvaluationInitializationService(
        ctx["project_repo"],
        ctx["research_repo"],
        ctx["planning_repo"],
        ctx["architecture_repo"],
        evaluation_repo,
    )
    init_svc.initialize_evaluation(
        ctx["project_id"],
        ctx["res_snap_id"],
        ctx["plan_snap_id"],
        ctx["arch_snap_id"],
    )

    coverage_svc = RequirementCoverageService(
        evaluation_repo,
        ctx["research_repo"],
        ctx["planning_repo"],
        ctx["architecture_repo"],
    )
    traceability_svc = TraceabilityEvaluationService(
        evaluation_repo,
        ctx["research_repo"],
        ctx["planning_repo"],
        ctx["architecture_repo"],
    )
    arch_svc = ArchitectureEvaluationService(
        evaluation_repo,
        ctx["architecture_repo"],
    )
    risk_svc = RiskEvaluationService(
        evaluation_repo,
        ctx["architecture_repo"],
    )
    quality_svc = QualityEvaluationService(
        evaluation_repo,
        ctx["architecture_repo"],
    )
    readiness_svc = ReadinessEvaluationService(evaluation_repo)
    summary_svc = EvaluationSummaryService(evaluation_repo)

    # 1. Evaluate coverage
    coverage = coverage_svc.evaluate_coverage(ctx["project_id"])
    assert len(coverage) == 2
    # Deliverable status check
    d_cov = next(c for c in coverage if c.requirement_type == "deliverable")
    assert d_cov.status == "satisfied"
    # Constraint status check
    c_cov = next(c for c in coverage if c.requirement_type == "constraint")
    assert c_cov.status == "satisfied"

    # 2. Evaluate traceability
    findings = traceability_svc.evaluate_traceability(ctx["project_id"])
    # Should have 0 broken links findings since our setup is valid
    assert len(findings) == 0

    # 3. Evaluate architecture
    findings = arch_svc.evaluate_architecture(ctx["project_id"])
    assert len(findings) == 0

    # 4. Evaluate risks
    findings = risk_svc.evaluate_risks(ctx["project_id"])
    assert len(findings) == 0

    # 5. Evaluate quality attributes
    findings = quality_svc.evaluate_quality_attributes(ctx["project_id"])
    assert len(findings) == 0

    # 6. Make readiness decision
    readiness_svc.make_readiness_decision(
        ctx["project_id"],
        True,
        "Architecture covers all deliverables and constraints with robust tracelinks",
    )

    eval_obj = evaluation_repo.get_by_project_id(ctx["project_id"])
    assert eval_obj is not None
    assert eval_obj.readiness_decision is not None
    assert eval_obj.readiness_decision.ready is True

    # 7. Submit for review & freeze
    summary_svc.submit_for_review(ctx["project_id"])
    snapshot = summary_svc.freeze_snapshot(
        ctx["project_id"], "Successful design evaluation pass"
    )

    eval_obj = evaluation_repo.get_by_project_id(ctx["project_id"])
    assert eval_obj is not None
    assert eval_obj.status == ArtifactStatus.APPROVED
    assert len(eval_obj.snapshots) == 1
    assert eval_obj.summary is not None
    assert eval_obj.summary.synthesis == "Successful design evaluation pass"
    assert eval_obj.summary.satisfied_requirements == 2

    # Verify snapshot
    assert snapshot.metadata.version == 1
    assert snapshot.readiness_decision.ready is True
    assert snapshot.summary.total_findings == 0
