from uuid import UUID, uuid4

from engine.domain.workspace import Workspace, WorkspaceArtifact


def test_workspace_artifact_construction() -> None:
    artifact = WorkspaceArtifact(
        name="README.md",
        path="README.md",
        description="Project documentation",
    )
    assert artifact.name == "README.md"
    assert artifact.path == "README.md"
    assert artifact.description == "Project documentation"


def test_workspace_defaults() -> None:
    project_id = uuid4()
    workspace = Workspace(project_id=project_id)

    assert isinstance(workspace.id, UUID)
    assert workspace.project_id == project_id
    assert workspace.artifacts == []
    assert workspace.context_variables == {}


def test_workspace_custom_values() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    artifact = WorkspaceArtifact(name="main.py", path="main.py")
    context = {"env": "development", "user": "test_user"}

    workspace = Workspace(
        id=workspace_id,
        project_id=project_id,
        artifacts=[artifact],
        context_variables=context,
    )

    assert workspace.id == workspace_id
    assert workspace.project_id == project_id
    assert len(workspace.artifacts) == 1
    assert workspace.artifacts[0].name == "main.py"
    assert workspace.context_variables == context
