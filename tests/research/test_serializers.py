from uuid import uuid4

from atlas_eng.engine.domain.enums import ResearchStatus
from atlas_eng.engine.domain.research import ProblemDefinition, Research
from atlas_eng.engine.research.serializers import (
    deserialize_research,
    serialize_research,
)


def test_serialize_deserialize_research() -> None:
    project_id = uuid4()
    problem = ProblemDefinition(statement="A problem", objectives=[])
    research = Research(
        project_id=project_id,
        status=ResearchStatus.IN_PROGRESS,
        problem_definition=problem,
    )

    data = serialize_research(research)
    assert isinstance(data, dict)
    assert data["project_id"] == str(project_id)
    assert data["status"] == "in_progress"

    deserialized = deserialize_research(data)
    assert deserialized.project_id == project_id
    assert deserialized.status == ResearchStatus.IN_PROGRESS
    assert deserialized.problem_definition is not None
    assert deserialized.problem_definition.statement == "A problem"
