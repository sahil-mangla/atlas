from pathlib import Path
from uuid import UUID, uuid4

from engine.ai.fs_repository import (
    FilesystemConversationRepository,
    FilesystemProposalRepository,
)
from engine.domain.ai import AIProposal, ContextPayload, PromptTemplateMetadata
from engine.domain.ai_drafts import ResearchProposalDraft
from engine.domain.conversation import ConversationMessage, ConversationSession
from engine.domain.enums import ConversationRole, ProposalStatus, ProposalType
from engine.domain.project import Project
from engine.project.repository import ProjectRepository


class DummyProjectRepo(ProjectRepository):
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.projects: list[Project] = []

    def get_project_path(self, project_id: UUID) -> Path:
        return self.tmp_path / str(project_id)

    def save(self, project: Project) -> None:
        pass

    def get_by_id(self, project_id: UUID) -> Project | None:
        return None

    def discover(self) -> list[Project]:
        return self.projects


def test_conversation_repository(tmp_path: Path) -> None:
    proj_repo = DummyProjectRepo(tmp_path)
    proj_id = uuid4()
    proj_repo.projects = [
        Project(id=proj_id, name="Test", description="Desc", objective="Obj")
    ]

    repo = FilesystemConversationRepository(proj_repo)

    session = ConversationSession(
        project_id=proj_id,
        title="Test Chat",
        messages=[
            ConversationMessage(role=ConversationRole.USER, content="ping"),
        ],
    )

    # Save
    repo.save(session)

    # Get by ID
    loaded = repo.get_by_id(session.id)
    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.title == "Test Chat"
    assert len(loaded.messages) == 1

    # Get by Project
    sessions = repo.get_by_project_id(proj_id)
    assert len(sessions) == 1
    assert sessions[0].id == session.id


def test_proposal_repository_survives_recreation(tmp_path: Path) -> None:
    proj_repo = DummyProjectRepo(tmp_path)
    proj_id = uuid4()
    proj_repo.projects = [
        Project(id=proj_id, name="Test", description="Desc", objective="Obj")
    ]
    proposal = AIProposal[ResearchProposalDraft](
        proposal_type=ProposalType.RESEARCH,
        status=ProposalStatus.DRAFT,
        prompt_metadata=PromptTemplateMetadata(
            version=1, supported_subsystem=ProposalType.RESEARCH
        ),
        context_used=ContextPayload(serialized_context=""),
        data=ResearchProposalDraft(problem_statement="p", objectives=["o"]),
    )
    FilesystemProposalRepository(proj_repo).save(proj_id, proposal)

    loaded = FilesystemProposalRepository(proj_repo).get_by_id(proposal.id)
    assert loaded is not None
    loaded_project, loaded_proposal = loaded
    assert loaded_project == proj_id
    assert loaded_proposal.data.problem_statement == "p"
