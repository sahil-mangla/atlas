"""AI Orchestration and Context Assembly services.

These services enforce the strict boundary between AI generation and 
domain state mutation.
"""

from typing import Any, cast
from uuid import UUID

from engine.ai.context import ContextStrategy
from engine.ai.exceptions import InvalidContextException, InvalidProposalException
from engine.ai.prompts import PromptTemplate
from engine.ai.provider import AIProvider
from engine.architecture.repository import ArchitectureRepository
from engine.domain.ai import (
    AIGenerationParameters,
    AIProposal,
    AIRequest,
    ContextPayload,
)
from engine.domain.enums import ProposalStatus
from engine.evaluation.repository import EvaluationRepository
from engine.memory.repository import MemoryRepository
from engine.planning.repository import PlanningRepository
from engine.research.repository import ResearchRepository


class ContextAssemblerService:
    """Collects and freezes approved domain snapshots into an immutable context payload."""

    def __init__(
        self,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
        architecture_repo: ArchitectureRepository,
        evaluation_repo: EvaluationRepository,
        memory_repo: MemoryRepository,
    ) -> None:
        self.research_repo = research_repo
        self.planning_repo = planning_repo
        self.architecture_repo = architecture_repo
        self.evaluation_repo = evaluation_repo
        self.memory_repo = memory_repo

    def assemble_context(self, project_id: UUID) -> ContextPayload:
        """Query subsystems for their latest approved snapshots and stringify them."""
        # For Stage 11, we stub the actual serialization logic but enforce the references.
        research = self.research_repo.get_by_project_id(project_id)
        planning = self.planning_repo.get_by_project_id(project_id)
        architecture = self.architecture_repo.get_by_project_id(project_id)
        evaluation = self.evaluation_repo.get_by_project_id(project_id)

        res_snap_id = research.snapshots[-1].metadata.id if research and research.snapshots else None
        plan_snap_id = planning.snapshots[-1].metadata.id if planning and planning.snapshots else None
        arch_snap_id = architecture.snapshots[-1].metadata.id if architecture and architecture.snapshots else None
        eval_snap_id = evaluation.snapshots[-1].metadata.id if evaluation and evaluation.snapshots else None

        # Build a textual dump of the active context (mocked for now)
        serialized = (
            f"Project {project_id} Context:\n"
            f"Research Snapshot: {res_snap_id}\n"
            f"Planning Snapshot: {plan_snap_id}\n"
            f"Architecture Snapshot: {arch_snap_id}\n"
            f"Evaluation Snapshot: {eval_snap_id}\n"
        )

        return ContextPayload(
            research_snapshot_id=res_snap_id,
            planning_snapshot_id=plan_snap_id,
            architecture_snapshot_id=arch_snap_id,
            evaluation_snapshot_id=eval_snap_id,
            memory_entries=[],
            serialized_context=serialized,
        )


class AIOrchestrationService:
    """Central engine that runs deterministic LLM prompts using a specific strategy.

    Critically, this service has NO access to repository `.save()` methods. It can
    only emit AIProposal objects.
    """

    def __init__(self, provider: AIProvider, context_strategy: ContextStrategy) -> None:
        self.provider = provider
        self.context_strategy = context_strategy

    def generate_proposal(
        self,
        template: PromptTemplate,
        raw_context: ContextPayload,
        user_instructions: str = "",
    ) -> AIProposal[dict[str, Any]]:
        """Generate a proposal.

        Args:
            template: The structured prompt template.
            raw_context: The assembled deterministic context.
            user_instructions: Optional user directions.

        Returns:
            A typed AIProposal holding the un-committed draft data.
        """
        # Apply the strategy (e.g. Identity compression)
        processed_context = self.context_strategy.apply(raw_context)

        # Build prompt
        prompt = template.build(processed_context, user_instructions)

        # Construct deterministic request
        request = AIRequest(
            prompt=prompt,
            context=processed_context,
            tools=[],  # Empty in Stage 11
            response_schema=template.expected_schema,
            parameters=AIGenerationParameters(),
        )

        # Invoke provider
        response = self.provider.generate(request)

        # For Stage 11, we stub the actual JSON parsing of `response.content`
        # In reality, this would be json.loads() or similar.
        parsed_data = {"raw_content": response.content}

        return AIProposal[dict[str, Any]](
            proposal_type=template.metadata.supported_subsystem,
            status=ProposalStatus.DRAFT,
            prompt_metadata=template.metadata,
            context_used=processed_context,
            data=parsed_data,
        )


class ProposalCommitService:
    """Handles the final mutation step after a proposal has been explicitly approved by human review."""

    def __init__(self) -> None:
        # In a real implementation, this service takes all the subsystem Domain Services 
        # (e.g., ResearchService, PlanningService) as dependencies.
        # It takes an APPROVED AIProposal and routes the generic .data to the actual 
        # service methods.
        pass

    def commit_proposal(self, proposal: AIProposal[Any]) -> None:
        """Route the proposal payload into the target repository.

        Args:
            proposal: The AIProposal. It MUST be APPROVED.
        """
        if proposal.status != ProposalStatus.APPROVED:
            raise InvalidProposalException("Only APPROVED proposals can be committed.")

        # Logic to cast proposal.data and call specific domain service method
        # E.g.
        # if proposal.proposal_type == ProposalType.RESEARCH:
        #     self.research_service.apply_draft(proposal.data)
        pass
