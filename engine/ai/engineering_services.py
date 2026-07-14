"""AI Engineering Services coordinating generation, validation, and commits."""

import json
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from engine.ai.exceptions import InvalidProposalException
from engine.ai.prompts import (
    ArchitecturePromptTemplate,
    EvaluationPromptTemplate,
    PlanningPromptTemplate,
    PromptTemplate,
    ResearchPromptTemplate,
)
from engine.ai.services import AIOrchestrationService, ContextAssemblerService
from engine.ai.unit_of_work import ProposalCommitUnitOfWork
from engine.architecture.repository import ArchitectureRepository
from engine.architecture.services import (
    ArchitectureCompositionService,
    ArchitecturalDecisionService,
    ArchitectureInitializationService,
    ArchitectureSummaryService,
    ComponentModelService,
    InterfaceContractService,
    RiskAnalysisService,
)
from engine.domain.ai import AIProposal
from engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    CommitResult,
    EvaluationProposalDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
from engine.domain.evaluation import EvaluationFinding
from engine.domain.enums import ProposalStatus, ProposalType
from engine.evaluation.repository import EvaluationRepository
from engine.evaluation.services import (
    EvaluationInitializationService,
    EvaluationSummaryService,
    ReadinessEvaluationService,
)
from engine.planning.repository import PlanningRepository
from engine.planning.services import (
    MilestonePlanningService,
    PlanningInitializationService,
    PlanningSummaryService,
    ScopePlanningService,
    TaskPlanningService,
)
from engine.research.repository import ResearchRepository
from engine.research.services import (
    OpportunityAnalysisService,
    ResearchCaptureService,
    ResearchInitializationService,
    ResearchOrganizationService,
    ResearchSummaryService,
)

T = TypeVar("T", bound=BaseModel)


# ==========================================
# Validator Interfaces & Implementations
# ==========================================


class ProposalValidator(Generic[T], ABC):
    """Protocol for checking semantic correctness of AI-generated drafts."""

    @abstractmethod
    def validate(self, draft: T) -> None:
        """Validate the draft model. Raise InvalidProposalException on failure."""
        pass


class ResearchProposalValidator(ProposalValidator[ResearchProposalDraft]):
    def validate(self, draft: ResearchProposalDraft) -> None:
        if not draft.problem_statement.strip():
            raise InvalidProposalException("Problem statement cannot be empty.")
        if not draft.objectives:
            raise InvalidProposalException("Research objectives list cannot be empty.")
        evidence_count = len(draft.evidence)
        for finding in draft.findings:
            if any(
                index < 0 or index >= evidence_count
                for index in finding.evidence_indices
            ):
                raise InvalidProposalException(
                    "Finding references an invalid evidence index."
                )
        finding_count = len(draft.findings)
        for constraint in draft.constraints:
            if any(
                index < 0 or index >= finding_count
                for index in constraint.finding_indices
            ):
                raise InvalidProposalException(
                    "Constraint references an invalid finding index."
                )
        for opportunity in draft.opportunities:
            if any(
                index < 0 or index >= finding_count
                for index in opportunity.finding_indices
            ):
                raise InvalidProposalException(
                    "Opportunity references an invalid finding index."
                )


class PlanningProposalValidator(ProposalValidator[PlanningProposalDraft]):
    def validate(self, draft: PlanningProposalDraft) -> None:
        if not draft.scope_statement.strip():
            raise InvalidProposalException("Scope statement cannot be empty.")
        if any(
            task.estimated_hours is not None
            for milestone in draft.milestones
            for epic in milestone.epics
            for task in epic.tasks
        ):
            raise InvalidProposalException(
                "Task estimates are not supported by the planning aggregate."
            )


class ArchitectureProposalValidator(ProposalValidator[ArchitectureProposalDraft]):
    def validate(self, draft: ArchitectureProposalDraft) -> None:
        if not draft.design_summary.strip():
            raise InvalidProposalException("Design summary cannot be empty.")
        component_names = [component.name.strip() for component in draft.components]
        if len(component_names) != len(set(component_names)):
            raise InvalidProposalException(
                "Architecture component names must be unique."
            )
        if any(not name for name in component_names):
            raise InvalidProposalException(
                "Architecture component names cannot be empty."
            )
        known_components = set(component_names)
        for component in draft.components:
            if not component.description.strip():
                raise InvalidProposalException(
                    "Component descriptions cannot be empty."
                )
            if any(
                dependency not in known_components or dependency == component.name
                for dependency in component.internal_dependencies
            ):
                raise InvalidProposalException(
                    "Architecture component dependency references an unknown or self component."
                )
        if any(
            not value.strip()
            for decision in draft.decisions
            for value in (
                decision.title,
                decision.status,
                decision.context,
                decision.decision,
                decision.consequences,
            )
        ):
            raise InvalidProposalException(
                "Architecture decisions require complete text fields."
            )
        if any(
            not value.strip()
            for risk in draft.risks
            for value in (risk.title, risk.description, risk.severity)
        ):
            raise InvalidProposalException(
                "Architecture risks require complete text fields."
            )


class EvaluationProposalValidator(ProposalValidator[EvaluationProposalDraft]):
    def validate(self, draft: EvaluationProposalDraft) -> None:
        if not draft.synthesis.strip():
            raise InvalidProposalException("Evaluation synthesis cannot be empty.")
        if any(
            not value.strip()
            for finding in draft.findings
            for value in (finding.title, finding.summary)
        ):
            raise InvalidProposalException(
                "Evaluation findings require title and summary."
            )


# ==========================================
# Transformer Interfaces & Implementations
# ==========================================


class ProposalTransformer(Generic[T], ABC):
    """Protocol mapping validated draft structures to subsystem domain services."""

    @abstractmethod
    def transform_and_commit(self, project_id: UUID, draft: T) -> UUID:
        """Map draft model to domain services and return the created Snapshot ID."""
        pass


class ResearchProposalTransformer(ProposalTransformer[ResearchProposalDraft]):
    def __init__(
        self,
        research_repo: ResearchRepository,
        research_init: ResearchInitializationService,
        research_capture: ResearchCaptureService,
        research_org: ResearchOrganizationService,
        opp_analysis: OpportunityAnalysisService,
        research_summary: ResearchSummaryService,
    ) -> None:
        self.research_repo = research_repo
        self.research_init = research_init
        self.research_capture = research_capture
        self.research_org = research_org
        self.opp_analysis = opp_analysis
        self.research_summary = research_summary

    def transform_and_commit(
        self, project_id: UUID, draft: ResearchProposalDraft
    ) -> UUID:
        # Step 1: Initialize research
        research = self.research_init.initialize_research(
            project_id=project_id,
            problem_statement=draft.problem_statement,
            objectives=draft.objectives,
        )

        # Step 2: Capture evidence
        evidence_ids = []
        for ev in draft.evidence:
            evidence = self.research_capture.add_evidence(
                project_id=project_id,
                type_=ev.type,
                title=ev.title,
                origin=ev.origin,
                citation=ev.citation,
                summary=ev.summary,
            )
            evidence_ids.append(evidence.id)

        # Step 3: Organize findings
        finding_ids = []
        for f in draft.findings:
            ref_ev_ids = [evidence_ids[idx] for idx in f.evidence_indices]
            finding = self.research_org.add_finding(
                project_id=project_id,
                title=f.title,
                summary=f.summary,
                evidence_ids=ref_ev_ids,
            )
            finding_ids.append(finding.id)

        # Step 4: Add constraints and assumptions
        for c in draft.constraints:
            ref_find_ids = [finding_ids[idx] for idx in c.finding_indices]
            self.research_org.add_constraint(
                project_id=project_id,
                description=c.description,
                impact=c.impact,
                finding_ids=ref_find_ids,
            )

        for a in draft.assumptions:
            self.research_org.add_assumption(
                project_id=project_id,
                description=a.description,
                risk=a.risk,
            )

        # Step 5: Add opportunities
        for o in draft.opportunities:
            ref_find_ids = [finding_ids[idx] for idx in o.finding_indices]
            self.opp_analysis.add_opportunity(
                project_id=project_id,
                title=o.title,
                description=o.description,
                finding_ids=ref_find_ids,
            )

        # Step 6: Finalize snapshot
        snapshot = self.research_summary.freeze_snapshot(
            project_id=project_id,
            synthesis="Synthesized automatically via AI Engineering Services.",
            key_takeaways=[f.title for f in draft.findings],
            confidence=0.9,
        )
        return snapshot.metadata.id


class PlanningProposalTransformer(ProposalTransformer[PlanningProposalDraft]):
    def __init__(
        self,
        planning_repo: PlanningRepository,
        research_repo: ResearchRepository,
        planning_init: PlanningInitializationService,
        scope_planning: ScopePlanningService,
        milestone_planning: MilestonePlanningService,
        task_planning: TaskPlanningService,
        planning_summary: PlanningSummaryService,
    ) -> None:
        self.planning_repo = planning_repo
        self.research_repo = research_repo
        self.planning_init = planning_init
        self.scope_planning = scope_planning
        self.milestone_planning = milestone_planning
        self.task_planning = task_planning
        self.planning_summary = planning_summary

    def transform_and_commit(
        self, project_id: UUID, draft: PlanningProposalDraft
    ) -> UUID:
        research = self.research_repo.get_by_project_id(project_id)
        if not research or not research.snapshots:
            raise InvalidProposalException(
                "Approved research snapshot required for planning."
            )
        research_snapshot_id = research.snapshots[-1].metadata.id

        # Step 1: Initialize planning
        self.planning_init.initialize_planning(project_id, research_snapshot_id)

        # Step 2: Set scope
        self.scope_planning.set_scope(
            project_id=project_id,
            statement=draft.scope_statement,
            deliverables=draft.deliverables,
        )

        # Step 3: Add Milestones, Epics, Tasks
        for m in draft.milestones:
            milestone = self.milestone_planning.add_milestone(
                project_id=project_id,
                title=m.title,
                description=m.description,
            )
            for e in m.epics:
                epic = self.milestone_planning.add_epic(
                    project_id=project_id,
                    milestone_id=milestone.id,
                    title=e.title,
                    description=e.description,
                )
                for t in e.tasks:
                    task = self.task_planning.add_task(
                        project_id=project_id,
                        epic_id=epic.id,
                        title=t.title,
                        description=t.description,
                    )
                    for st in t.subtasks:
                        self.task_planning.add_subtask(
                            project_id=project_id,
                            task_id=task.id,
                            title=st.title,
                        )

        # Step 4: Freeze snapshot
        snapshot = self.planning_summary.freeze_snapshot(
            project_id=project_id,
            research_snapshot_id=research_snapshot_id,
            synthesis="Plan built automatically via AI Engineering Services.",
        )
        return snapshot.metadata.id


class ArchitectureProposalTransformer(ProposalTransformer[ArchitectureProposalDraft]):
    def __init__(
        self,
        architecture_repo: ArchitectureRepository,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
        arch_init: ArchitectureInitializationService,
        arch_comp: ArchitectureCompositionService,
        arch_summary: ArchitectureSummaryService,
        component_model: ComponentModelService,
        adr_service: ArchitecturalDecisionService,
        interface_service: InterfaceContractService,
        risk_service: RiskAnalysisService,
    ) -> None:
        self.architecture_repo = architecture_repo
        self.research_repo = research_repo
        self.planning_repo = planning_repo
        self.arch_init = arch_init
        self.arch_comp = arch_comp
        self.arch_summary = arch_summary
        self.component_model = component_model
        self.adr_service = adr_service
        self.interface_service = interface_service
        self.risk_service = risk_service

    def transform_and_commit(
        self, project_id: UUID, draft: ArchitectureProposalDraft
    ) -> UUID:
        research = self.research_repo.get_by_project_id(project_id)
        planning = self.planning_repo.get_by_project_id(project_id)
        if not research or not research.snapshots:
            raise InvalidProposalException("Approved research snapshot required.")
        if not planning or not planning.snapshots:
            raise InvalidProposalException("Approved planning snapshot required.")

        res_snap_id = research.snapshots[-1].metadata.id
        plan_snap_id = planning.snapshots[-1].metadata.id

        # Step 1: Initialize
        self.arch_init.initialize_architecture(
            project_id=project_id,
            research_snapshot_id=res_snap_id,
            planning_snapshot_id=plan_snap_id,
        )

        # Step 2: Set summary
        self.arch_comp.set_design_summary(project_id, draft.design_summary)

        # Step 3: Add drivers and components.
        for d in draft.drivers:
            self.arch_comp.add_architecture_driver(
                project_id=project_id,
                name=f"{d.driver_type} Driver",
                description=d.description,
                driver_type=d.driver_type,
                source_finding_ids=[],
                source_objective_ids=[],
            )

        component_ids: dict[str, UUID] = {}
        for component in draft.components:
            responsibilities = list(component.responsibilities)
            if component.description not in responsibilities:
                responsibilities.insert(0, component.description)
            created = self.component_model.add_component(
                project_id=project_id,
                name=component.name,
                responsibilities=responsibilities,
                owned_data=component.owned_data,
                external_dependencies=component.external_dependencies,
            )
            component_ids[component.name] = created.id
            for interface in component.public_interfaces:
                self.interface_service.add_interface_contract(
                    project_id=project_id,
                    component_id=created.id,
                    name=interface,
                    description="",
                    protocol="unspecified",
                    input_schema="",
                    output_schema="",
                )
        for component in draft.components:
            for dependency in component.internal_dependencies:
                self.component_model.add_internal_dependency(
                    project_id=project_id,
                    component_id=component_ids[component.name],
                    depends_on_id=component_ids[dependency],
                )

        for decision in draft.decisions:
            self.adr_service.add_adr(
                project_id=project_id,
                title=decision.title,
                context=decision.context,
                problem_statement=decision.context,
                decision=decision.decision,
                rationale=f"Status: {decision.status}. {decision.decision}",
                consequences=decision.consequences,
            )
        for risk in draft.risks:
            self.risk_service.register_risk(
                project_id=project_id,
                description=f"{risk.title}: {risk.description}",
                severity=risk.severity,
                likelihood="unspecified",
                impact=risk.description,
                mitigation="",
                owner="unassigned",
            )

        # Step 4: Finalize snapshot
        self.arch_summary.submit_for_review(project_id)
        snapshot = self.arch_summary.freeze_snapshot(
            project_id=project_id,
            planning_snapshot_id=plan_snap_id,
            research_snapshot_id=res_snap_id,
            synthesis="Architecture generated via AI Engineering Services.",
        )
        return snapshot.metadata.id


class EvaluationProposalTransformer(ProposalTransformer[EvaluationProposalDraft]):
    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
        architecture_repo: ArchitectureRepository,
        eval_init: EvaluationInitializationService,
        eval_summary: EvaluationSummaryService,
        readiness_service: ReadinessEvaluationService,
    ) -> None:
        self.evaluation_repo = evaluation_repo
        self.research_repo = research_repo
        self.planning_repo = planning_repo
        self.architecture_repo = architecture_repo
        self.eval_init = eval_init
        self.eval_summary = eval_summary
        self.readiness_service = readiness_service

    def transform_and_commit(
        self, project_id: UUID, draft: EvaluationProposalDraft
    ) -> UUID:
        research = self.research_repo.get_by_project_id(project_id)
        planning = self.planning_repo.get_by_project_id(project_id)
        architecture = self.architecture_repo.get_by_project_id(project_id)

        if not research or not research.snapshots:
            raise InvalidProposalException("Research snapshot required for evaluation.")
        if not planning or not planning.snapshots:
            raise InvalidProposalException("Planning snapshot required for evaluation.")
        if not architecture or not architecture.snapshots:
            raise InvalidProposalException(
                "Architecture snapshot required for evaluation."
            )

        res_snap_id = research.snapshots[-1].metadata.id
        plan_snap_id = planning.snapshots[-1].metadata.id
        arch_snap_id = architecture.snapshots[-1].metadata.id

        # Step 1: Initialize
        self.eval_init.initialize_evaluation(
            project_id=project_id,
            research_snapshot_id=res_snap_id,
            planning_snapshot_id=plan_snap_id,
            architecture_snapshot_id=arch_snap_id,
        )

        evaluation = self.evaluation_repo.get_by_project_id(project_id)
        if evaluation is None:
            raise InvalidProposalException("Evaluation initialization failed.")
        for finding in draft.findings:
            evaluation.findings.append(
                EvaluationFinding(
                    severity=finding.severity,
                    category=finding.category,
                    description=finding.title,
                    evidence=finding.summary,
                    recommendation="Review and resolve this finding.",
                )
            )
        self.evaluation_repo.save(evaluation)
        self.eval_summary.submit_for_review(project_id)
        self.readiness_service.make_readiness_decision(
            project_id,
            ready=not any(f.severity.value == "blocking" for f in evaluation.findings),
            justification=draft.synthesis,
        )

        # Step 2: Freeze snapshot
        snapshot = self.eval_summary.freeze_snapshot(
            project_id=project_id,
            synthesis=draft.synthesis,
        )
        return snapshot.metadata.id


# ==========================================
# Standardized AI Engineering Service
# ==========================================


class AIEngineeringService(Generic[T], ABC):
    """Common interface for orchestrating AI generation processes."""

    def __init__(
        self,
        orchestrator: AIOrchestrationService,
        context_assembler: ContextAssemblerService,
        template: PromptTemplate,
        draft_cls: type[T],
    ) -> None:
        self.orchestrator = orchestrator
        self.context_assembler = context_assembler
        self.template = template
        self.draft_cls = draft_cls

    def generate(self, project_id: UUID, user_instructions: str = "") -> AIProposal[T]:
        """Generate a strongly typed proposal.

        Retrieves deterministic context, triggers generation, and parses outcomes.
        """
        # Assemble immutable context
        context = self.context_assembler.assemble_context(project_id)

        # Generate proposal dictionary via underlying orchestrator
        raw_proposal = self.orchestrator.generate_proposal(
            template=self.template,
            raw_context=context,
            user_instructions=user_instructions,
        )

        # Parse string output into strongly-typed draft
        raw_content = raw_proposal.data.get("raw_content", "{}")
        try:
            parsed_json = json.loads(raw_content)
            typed_draft = self.draft_cls.model_validate(parsed_json)
        except Exception as e:
            raise InvalidProposalException(
                f"Failed to parse generation into typed draft: {e}"
            ) from e

        # Wrap in generic proposal structure
        return AIProposal[T](
            proposal_type=raw_proposal.proposal_type,
            status=raw_proposal.status,
            prompt_metadata=raw_proposal.prompt_metadata,
            context_used=raw_proposal.context_used,
            data=typed_draft,
        )


class ResearchAIEngineeringService(AIEngineeringService[ResearchProposalDraft]):
    def __init__(
        self,
        orchestrator: AIOrchestrationService,
        context_assembler: ContextAssemblerService,
    ) -> None:
        super().__init__(
            orchestrator=orchestrator,
            context_assembler=context_assembler,
            template=ResearchPromptTemplate(),
            draft_cls=ResearchProposalDraft,
        )


class PlanningAIEngineeringService(AIEngineeringService[PlanningProposalDraft]):
    def __init__(
        self,
        orchestrator: AIOrchestrationService,
        context_assembler: ContextAssemblerService,
    ) -> None:
        super().__init__(
            orchestrator=orchestrator,
            context_assembler=context_assembler,
            template=PlanningPromptTemplate(),
            draft_cls=PlanningProposalDraft,
        )


class ArchitectureAIEngineeringService(AIEngineeringService[ArchitectureProposalDraft]):
    def __init__(
        self,
        orchestrator: AIOrchestrationService,
        context_assembler: ContextAssemblerService,
    ) -> None:
        super().__init__(
            orchestrator=orchestrator,
            context_assembler=context_assembler,
            template=ArchitecturePromptTemplate(),
            draft_cls=ArchitectureProposalDraft,
        )


class EvaluationAIEngineeringService(AIEngineeringService[EvaluationProposalDraft]):
    def __init__(
        self,
        orchestrator: AIOrchestrationService,
        context_assembler: ContextAssemblerService,
    ) -> None:
        super().__init__(
            orchestrator=orchestrator,
            context_assembler=context_assembler,
            template=EvaluationPromptTemplate(),
            draft_cls=EvaluationProposalDraft,
        )


# ==========================================
# Proposal Commit Service
# ==========================================


class ProposalCommitService:
    """Manages validated commits with deterministic filesystem rollback."""

    def __init__(
        self,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
        architecture_repo: ArchitectureRepository,
        evaluation_repo: EvaluationRepository,
        # Transformers
        research_transformer: ResearchProposalTransformer,
        planning_transformer: PlanningProposalTransformer,
        architecture_transformer: ArchitectureProposalTransformer,
        evaluation_transformer: EvaluationProposalTransformer,
        # Validators
        research_validator: ResearchProposalValidator,
        planning_validator: PlanningProposalValidator,
        architecture_validator: ArchitectureProposalValidator,
        evaluation_validator: EvaluationProposalValidator,
    ) -> None:
        self.research_repo = research_repo
        self.planning_repo = planning_repo
        self.architecture_repo = architecture_repo
        self.evaluation_repo = evaluation_repo

        self.transformers: dict[ProposalType, ProposalTransformer[Any]] = {
            ProposalType.RESEARCH: research_transformer,
            ProposalType.PLANNING: planning_transformer,
            ProposalType.ARCHITECTURE: architecture_transformer,
            ProposalType.EVALUATION: evaluation_transformer,
        }
        self.validators: dict[ProposalType, ProposalValidator[Any]] = {
            ProposalType.RESEARCH: research_validator,
            ProposalType.PLANNING: planning_validator,
            ProposalType.ARCHITECTURE: architecture_validator,
            ProposalType.EVALUATION: evaluation_validator,
        }

    def commit_proposal(
        self, project_id: UUID, proposal: AIProposal[Any]
    ) -> CommitResult:
        """Validate, transform, and commit a proposal with rollback on failure."""
        if proposal.status != ProposalStatus.APPROVED:
            return CommitResult(
                success=False,
                errors=["Only APPROVED proposals can be committed."],
            )

        # 1. Select components
        ptype = proposal.proposal_type
        transformer = self.transformers.get(ptype)
        validator = self.validators.get(ptype)

        if not transformer or not validator:
            return CommitResult(
                success=False,
                errors=[f"Unsupported proposal type: {ptype}"],
            )

        # 2. Run Validation
        try:
            validator.validate(proposal.data)
        except InvalidProposalException as e:
            return CommitResult(success=False, errors=[str(e)])

        # 3. Capture filesystem-restorable state before mutation.
        unit_of_work = ProposalCommitUnitOfWork(
            project_id,
            (
                self.research_repo,
                self.planning_repo,
                self.architecture_repo,
                self.evaluation_repo,
            ),
        )
        unit_of_work.begin()

        # 4. Transform and commit.
        try:
            snapshot_id = transformer.transform_and_commit(project_id, proposal.data)
            return CommitResult(success=True, committed_snapshot_id=snapshot_id)
        except Exception as e:
            try:
                unit_of_work.rollback()
            except Exception as rollback_error:
                return CommitResult(
                    success=False,
                    errors=[f"Commit failed and rollback failed: {rollback_error}"],
                )

            return CommitResult(
                success=False,
                errors=[f"Commit failed; restored original state. Error: {e}"],
            )
