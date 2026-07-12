from datetime import datetime
from uuid import UUID, uuid4

from engine.domain.memory import EngineeringDecision, Memory, MemoryEntry


def test_engineering_decision() -> None:
    decision = EngineeringDecision(
        title="Setup Db",
        context="DB initialization needed",
        rationale="We need local databases",
    )
    assert isinstance(decision.id, UUID)
    assert decision.title == "Setup Db"
    assert decision.context == "DB initialization needed"
    assert decision.rationale == "We need local databases"
    assert isinstance(decision.recorded_at, datetime)


def test_memory_entry() -> None:
    entry = MemoryEntry(
        summary="User greeting",
        content="Hello world",
        source="user",
    )
    assert isinstance(entry.id, UUID)
    assert entry.summary == "User greeting"
    assert entry.content == "Hello world"
    assert entry.source == "user"
    assert isinstance(entry.recorded_at, datetime)


def test_memory_defaults() -> None:
    project_id = uuid4()
    memory = Memory(project_id=project_id)
    assert isinstance(memory.id, UUID)
    assert memory.project_id == project_id
    assert memory.engineering_decisions == []
    assert memory.knowledge_entries == []
    assert memory.lessons_learned == []


def test_memory_custom() -> None:
    mem_id = uuid4()
    project_id = uuid4()
    decision = EngineeringDecision(title="Use PG", context="ctx", rationale="rat")
    entry = MemoryEntry(summary="User query", content="select *")

    memory = Memory(
        id=mem_id,
        project_id=project_id,
        engineering_decisions=[decision],
        knowledge_entries=[entry],
        lessons_learned=["Always test config first"],
    )

    assert memory.id == mem_id
    assert memory.project_id == project_id
    assert len(memory.engineering_decisions) == 1
    assert memory.engineering_decisions[0].title == "Use PG"
    assert len(memory.knowledge_entries) == 1
    assert memory.knowledge_entries[0].summary == "User query"
    assert memory.lessons_learned == ["Always test config first"]
