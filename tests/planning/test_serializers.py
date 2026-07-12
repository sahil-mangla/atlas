from uuid import uuid4

from engine.domain.enums import PlanningStatus
from engine.domain.planning import Planning
from engine.planning.serializers import deserialize_planning, serialize_planning


def test_serialize_deserialize_planning() -> None:
    project_id = uuid4()
    planning = Planning(
        project_id=project_id,
        status=PlanningStatus.DRAFT,
    )

    data = serialize_planning(planning)
    assert isinstance(data, dict)
    assert data["project_id"] == str(project_id)
    assert data["status"] == "draft"

    deserialized = deserialize_planning(data)
    assert deserialized.project_id == project_id
    assert deserialized.status == PlanningStatus.DRAFT
    assert deserialized.scope_definition is None
