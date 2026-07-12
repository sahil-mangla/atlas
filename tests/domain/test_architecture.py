from datetime import datetime
from uuid import UUID, uuid4

from engine.domain.architecture import (
    ArchitecturalComponent,
    ArchitecturalDecision,
    Architecture,
)


def test_architectural_component() -> None:
    component = ArchitecturalComponent(
        name="API Gateway",
        responsibility="Routes external calls",
        interfaces=["REST API", "gRPC"],
        collaborators=["Auth Subsystem", "Order Subsystem"],
    )
    assert isinstance(component.id, UUID)
    assert component.name == "API Gateway"
    assert component.responsibility == "Routes external calls"
    assert component.interfaces == ["REST API", "gRPC"]
    assert component.collaborators == ["Auth Subsystem", "Order Subsystem"]


def test_architectural_decision() -> None:
    decision = ArchitecturalDecision(
        title="Use PostgreSQL",
        context="Need structured storage",
        decision="Adopt PostgreSQL",
        rationale="Strong reliability and ACID guarantees",
        consequences="Adds deployment complexity",
    )
    assert isinstance(decision.id, UUID)
    assert decision.title == "Use PostgreSQL"
    assert decision.context == "Need structured storage"
    assert decision.decision == "Adopt PostgreSQL"
    assert decision.rationale == "Strong reliability and ACID guarantees"
    assert decision.consequences == "Adds deployment complexity"
    assert isinstance(decision.recorded_at, datetime)


def test_architecture_defaults() -> None:
    project_id = uuid4()
    architecture = Architecture(project_id=project_id)
    assert isinstance(architecture.id, UUID)
    assert architecture.project_id == project_id
    assert architecture.design_summary == ""
    assert architecture.components == []
    assert architecture.decisions == []
    assert architecture.constraints == []
    assert architecture.assumptions == []


def test_architecture_custom() -> None:
    arch_id = uuid4()
    project_id = uuid4()
    component = ArchitecturalComponent(name="Gateway", responsibility="route")
    decision = ArchitecturalDecision(
        title="Use PG", context="ctx", decision="pg", rationale="rat"
    )

    architecture = Architecture(
        id=arch_id,
        project_id=project_id,
        design_summary="Microservices paradigm",
        components=[component],
        decisions=[decision],
        constraints=["Max latency 200ms"],
        assumptions=["Standard DB scaling works"],
    )

    assert architecture.id == arch_id
    assert architecture.project_id == project_id
    assert architecture.design_summary == "Microservices paradigm"
    assert len(architecture.components) == 1
    assert architecture.components[0].name == "Gateway"
    assert len(architecture.decisions) == 1
    assert architecture.decisions[0].title == "Use PG"
    assert architecture.constraints == ["Max latency 200ms"]
    assert architecture.assumptions == ["Standard DB scaling works"]
