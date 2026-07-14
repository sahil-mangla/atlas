from datetime import datetime
from uuid import UUID, uuid4

from engine.domain.architecture import (
    ArchitecturalDecision,
    Architecture,
    ArchitectureComponent,
    ArchitectureDriver,
    ArchitectureSnapshot,
    ArchitectureSummary,
    Assumption,
    Constraint,
    InterfaceContract,
    QualityAttribute,
    Risk,
)
from engine.domain.enums import ArchitectureStatus
from engine.domain.metadata import ArtifactMetadata


def test_interface_contract() -> None:
    contract = InterfaceContract(
        name="GetOrder",
        description="Retrieve order by ID",
        protocol="gRPC",
        input_schema="OrderRequest",
        output_schema="OrderResponse",
    )
    assert isinstance(contract.id, UUID)
    assert contract.name == "GetOrder"
    assert contract.protocol == "gRPC"


def test_architecture_driver() -> None:
    finding_id = uuid4()
    objective_id = uuid4()
    driver = ArchitectureDriver(
        name="Scalability Requirement",
        description="Must handle 10k RPS",
        driver_type="Quality Attribute",
        source_finding_ids=[finding_id],
        source_objective_ids=[objective_id],
    )
    assert isinstance(driver.id, UUID)
    assert driver.name == "Scalability Requirement"
    assert driver.source_finding_ids == [finding_id]
    assert driver.source_objective_ids == [objective_id]


def test_architecture_component() -> None:
    contract = InterfaceContract(
        name="API", description="d", protocol="REST", input_schema="in", output_schema="out"
    )
    adr_id = uuid4()
    risk_id = uuid4()
    component = ArchitectureComponent(
        name="API Gateway",
        responsibilities=["Route calls", "Auth"],
        public_interfaces=[contract],
        owned_data=["order-db"],
        internal_dependencies=[uuid4()],
        external_dependencies=["Stripe API"],
        related_adrs=[adr_id],
        related_risks=[risk_id],
    )
    assert isinstance(component.id, UUID)
    assert component.name == "API Gateway"
    assert component.responsibilities == ["Route calls", "Auth"]
    assert component.public_interfaces == [contract]
    assert component.owned_data == ["order-db"]
    assert len(component.internal_dependencies) == 1
    assert component.external_dependencies == ["Stripe API"]
    assert component.related_adrs == [adr_id]
    assert component.related_risks == [risk_id]


def test_architectural_decision() -> None:
    constraint_id = uuid4()
    finding_id = uuid4()
    decision = ArchitecturalDecision(
        title="Use PostgreSQL",
        context="Need structured storage",
        problem_statement="Choose persistent store",
        decision="Adopt PostgreSQL",
        rationale="Strong reliability",
        alternatives_considered=["MySQL", "DynamoDB"],
        reasons_rejected=["No ACID", "No JSON support"],
        trade_offs=["Deployment overhead"],
        consequences="Adds complexity",
        related_constraints=[constraint_id],
        related_research_findings=[finding_id],
    )
    assert isinstance(decision.id, UUID)
    assert decision.title == "Use PostgreSQL"
    assert decision.context == "Need structured storage"
    assert decision.decision == "Adopt PostgreSQL"
    assert decision.rationale == "Strong reliability"
    assert decision.alternatives_considered == ["MySQL", "DynamoDB"]
    assert decision.reasons_rejected == ["No ACID", "No JSON support"]
    assert decision.trade_offs == ["Deployment overhead"]
    assert decision.consequences == "Adds complexity"
    assert decision.related_constraints == [constraint_id]
    assert decision.related_research_findings == [finding_id]
    assert isinstance(decision.recorded_at, datetime)


def test_risk() -> None:
    adr_id = uuid4()
    risk = Risk(
        description="Database load",
        severity="high",
        likelihood="medium",
        impact="high",
        mitigation="Add read replicas",
        owner="ops-team",
        related_decision_id=adr_id,
    )
    assert isinstance(risk.id, UUID)
    assert risk.description == "Database load"
    assert risk.severity == "high"
    assert risk.related_decision_id == adr_id


def test_constraint() -> None:
    research_constraint_id = uuid4()
    c = Constraint(
        description="Must be open source",
        impact="Limits vendor options",
        related_research_constraint_id=research_constraint_id,
    )
    assert isinstance(c.id, UUID)
    assert c.description == "Must be open source"
    assert c.related_research_constraint_id == research_constraint_id


def test_assumption() -> None:
    research_assumption_id = uuid4()
    a = Assumption(
        description="Docker is installed",
        risk="Will fail to build",
        related_research_assumption_id=research_assumption_id,
    )
    assert isinstance(a.id, UUID)
    assert a.description == "Docker is installed"
    assert a.related_research_assumption_id == research_assumption_id


def test_quality_attribute() -> None:
    qa = QualityAttribute(
        name="Security",
        description="Encrypt all data",
        mitigation_strategy="AES-256",
        related_adrs=[uuid4()],
    )
    assert isinstance(qa.id, UUID)
    assert qa.name == "Security"
    assert len(qa.related_adrs) == 1


def test_architecture_defaults() -> None:
    project_id = uuid4()
    architecture = Architecture(project_id=project_id)
    assert isinstance(architecture.id, UUID)
    assert architecture.project_id == project_id
    assert architecture.status == ArchitectureStatus.DRAFT
    assert architecture.design_summary == ""
    assert architecture.components == []
    assert architecture.decisions == []
    assert architecture.constraints == []
    assert architecture.assumptions == []
    assert architecture.drivers == []
    assert architecture.quality_attributes == []
    assert architecture.summary is None
    assert architecture.snapshots == []


def test_architecture_snapshot() -> None:
    summary = ArchitectureSummary(
        synthesis="Overall design completed",
        total_components=1,
        total_adrs=1,
        total_risks=1,
    )
    snapshot = ArchitectureSnapshot(
        metadata=ArtifactMetadata(version=1),
        planning_snapshot_id=uuid4(),
        research_snapshot_id=uuid4(),
        drivers=[],
        components=[],
        decisions=[],
        risks=[],
        constraints=[],
        assumptions=[],
        quality_attributes=[],
        summary=summary,
    )
    assert snapshot.metadata.version == 1
    assert snapshot.summary.synthesis == "Overall design completed"
