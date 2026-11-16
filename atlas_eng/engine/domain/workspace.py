"""Workspace domain model for the ATLAS platform.

Workspace models the engineering environment as a logical catalog of
artifacts and session context — without coupling to any filesystem API,
OS path type, or storage technology.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WorkspaceArtifact(BaseModel):
    """A catalogued artifact within the engineering workspace.

    Represents a logical reference to a file, document, or asset using
    plain string identifiers, independent of any OS or filesystem API.
    """

    name: str = Field(
        description="Human-readable artifact name.",
    )
    path: str = Field(
        description="Relative path string identifying the artifact location.",
    )
    description: str = Field(
        default="",
        description="Optional description of the artifact's purpose or role.",
    )


class Workspace(BaseModel):
    """The engineering environment where software development takes place.

    Workspace maintains a technology-independent catalog of project artifacts
    and active session context variables. It does not couple to OS-specific
    path types, file handles, or execution environments.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique workspace identifier.",
    )
    project_id: UUID = Field(
        description="Reference to the owning Project.",
    )
    artifacts: list[WorkspaceArtifact] = Field(
        default_factory=list,
        description="Catalog of files, documents, and assets in the workspace.",
    )
    context_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Active session-level configuration and context parameters.",
    )
