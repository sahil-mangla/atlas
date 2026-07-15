"""Services managing the Evaluation subsystem assessment lifecycle."""

from uuid import UUID

from engine.architecture.repository import ArchitectureRepository
from engine.domain.enums import (
    FindingCategory,
    FindingSeverity,
)
from engine.domain.evaluation import (
    Evaluation,
    EvaluationFinding,
    EvaluationSnapshot,
    EvaluationSummary,
    ReadinessDecision,
    RequirementCoverage,
)
from engine.domain.metadata import ArtifactMetadata, ArtifactStatus
from engine.evaluation.exceptions import (
    EvaluationNotFoundException,
    InvalidEvaluationOperationException,
)
from engine.evaluation.repository import EvaluationRepository
from engine.planning.repository import PlanningRepository
from engine.project.repository import ProjectRepository
from engine.research.repository import ResearchRepository


def _ensure_mutable(evaluation: Evaluation) -> None:
    """Ensure the evaluation aggregate is in an editable state."""
    if evaluation.status in (ArtifactStatus.APPROVED, ArtifactStatus.ARCHIVED):
        raise InvalidEvaluationOperationException(
            "Cannot mutate evaluation that is APPROVED or ARCHIVED."
        )


class EvaluationInitializationService:
    """Handles creating the initial evaluation aggregate state for a project."""

    def __init__(
        self,
        project_repo: ProjectRepository,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
        architecture_repo: ArchitectureRepository,
        evaluation_repo: EvaluationRepository,
    ) -> None:
        self.project_repo = project_repo
        self.research_repo = research_repo
        self.planning_repo = planning_repo
        self.architecture_repo = architecture_repo
        self.evaluation_repo = evaluation_repo

    def initialize_evaluation(
        self,
        project_id: UUID,
        research_snapshot_id: UUID,
        planning_snapshot_id: UUID,
        architecture_snapshot_id: UUID,
    ) -> Evaluation:
        """Create a new evaluation context based on approved baseline snapshots."""
        if not self.project_repo.get_by_id(project_id):
            raise EvaluationNotFoundException(f"Project {project_id} does not exist.")

        if self.evaluation_repo.exists(project_id):
            raise InvalidEvaluationOperationException(
                f"Evaluation already initialized for project {project_id}."
            )

        # Validate research snapshot is approved and exists
        research = self.research_repo.get_by_project_id(project_id)
        if not research or not any(
            s.metadata.id == research_snapshot_id for s in research.snapshots
        ):
            raise InvalidEvaluationOperationException(
                f"Approved research snapshot {research_snapshot_id} not found."
            )

        # Validate planning snapshot is approved and exists
        planning = self.planning_repo.get_by_project_id(project_id)
        if not planning or not any(
            s.metadata.id == planning_snapshot_id for s in planning.snapshots
        ):
            raise InvalidEvaluationOperationException(
                f"Approved planning snapshot {planning_snapshot_id} not found."
            )

        # Validate architecture snapshot is approved and exists
        architecture = self.architecture_repo.get_by_project_id(project_id)
        if not architecture or not any(
            s.metadata.id == architecture_snapshot_id for s in architecture.snapshots
        ):
            raise InvalidEvaluationOperationException(
                f"Approved architecture snapshot {architecture_snapshot_id} not found."
            )

        evaluation = Evaluation(
            project_id=project_id,
            status=ArtifactStatus.DRAFT,
            research_snapshot_id=research_snapshot_id,
            planning_snapshot_id=planning_snapshot_id,
            architecture_snapshot_id=architecture_snapshot_id,
        )
        self.evaluation_repo.save(evaluation)
        return evaluation


class RequirementCoverageService:
    """Evaluates whether planning deliverables and research constraints are met in design."""

    def __init__(
        self,
        repository: EvaluationRepository,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
        architecture_repo: ArchitectureRepository,
    ) -> None:
        self.repository = repository
        self.research_repo = research_repo
        self.planning_repo = planning_repo
        self.architecture_repo = architecture_repo

    def evaluate_coverage(self, project_id: UUID) -> list[RequirementCoverage]:
        """Audit the architecture against research constraints and planning deliverables."""
        evaluation = self.repository.get_by_project_id(project_id)
        if not evaluation:
            raise EvaluationNotFoundException()
        _ensure_mutable(evaluation)

        research = self.research_repo.get_by_project_id(project_id)
        planning = self.planning_repo.get_by_project_id(project_id)
        architecture = self.architecture_repo.get_by_project_id(project_id)

        if not research or not planning or not architecture:
            raise InvalidEvaluationOperationException(
                "Snapshots missing from repository."
            )

        r_snap = next(
            s
            for s in research.snapshots
            if s.metadata.id == evaluation.research_snapshot_id
        )
        p_snap = next(
            s
            for s in planning.snapshots
            if s.metadata.id == evaluation.planning_snapshot_id
        )
        a_snap = next(
            s
            for s in architecture.snapshots
            if s.metadata.id == evaluation.architecture_snapshot_id
        )

        coverage_list: list[RequirementCoverage] = []

        # 1. Evaluate Planning Deliverables (Objectives)
        for d in p_snap.scope_definition.deliverables:
            # Trace deliverable through drivers and ADRs
            matching_drivers = [
                drv for drv in a_snap.drivers if d.id in drv.source_objective_ids
            ]
            if not matching_drivers:
                coverage_list.append(
                    RequirementCoverage(
                        requirement_id=d.id,
                        requirement_type="deliverable",
                        description=d.title,
                        status="unsatisfied",
                        justification="No architecture driver maps to this deliverable.",
                    )
                )
            else:
                has_decisions = any(drv.target_adr_ids for drv in matching_drivers)
                if has_decisions:
                    coverage_list.append(
                        RequirementCoverage(
                            requirement_id=d.id,
                            requirement_type="deliverable",
                            description=d.title,
                            status="satisfied",
                            justification="Deliverable addressed by architecture drivers and implementing ADRs.",
                        )
                    )
                else:
                    coverage_list.append(
                        RequirementCoverage(
                            requirement_id=d.id,
                            requirement_type="deliverable",
                            description=d.title,
                            status="partially_satisfied",
                            justification="Mapped to architecture drivers but lacks concrete ADR design decisions.",
                        )
                    )

        # 2. Evaluate Research Constraints
        for c in r_snap.constraints:
            matching_constraints = [
                ac
                for ac in a_snap.constraints
                if ac.related_research_constraint_id == c.id
            ]
            if not matching_constraints:
                coverage_list.append(
                    RequirementCoverage(
                        requirement_id=c.id,
                        requirement_type="constraint",
                        description=c.description,
                        status="unsatisfied",
                        justification="No architectural constraint addresses this research constraint.",
                    )
                )
            else:
                # Check if mapped architecture constraint is linked to an ADR
                ac_ids = {ac.id for ac in matching_constraints}
                linked_to_adr = any(
                    c_id in adr.related_constraints
                    for adr in a_snap.decisions
                    for c_id in ac_ids
                )
                if linked_to_adr:
                    coverage_list.append(
                        RequirementCoverage(
                            requirement_id=c.id,
                            requirement_type="constraint",
                            description=c.description,
                            status="satisfied",
                            justification="Research constraint mapped to architectural constraints and enforced in ADR decisions.",
                        )
                    )
                else:
                    coverage_list.append(
                        RequirementCoverage(
                            requirement_id=c.id,
                            requirement_type="constraint",
                            description=c.description,
                            status="partially_satisfied",
                            justification="Mapped to architectural constraints but lacks concrete enforcement in ADR decisions.",
                        )
                    )

        evaluation.coverage = coverage_list
        self.repository.save(evaluation)
        return coverage_list


class TraceabilityEvaluationService:
    """Audits design trace lineage and registers findings for broken/missing relationships."""

    def __init__(
        self,
        repository: EvaluationRepository,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
        architecture_repo: ArchitectureRepository,
    ) -> None:
        self.repository = repository
        self.research_repo = research_repo
        self.planning_repo = planning_repo
        self.architecture_repo = architecture_repo

    def evaluate_traceability(self, project_id: UUID) -> list[EvaluationFinding]:
        """Audit trace relationships of Architectural Decisions."""
        evaluation = self.repository.get_by_project_id(project_id)
        if not evaluation:
            raise EvaluationNotFoundException()
        _ensure_mutable(evaluation)

        research = self.research_repo.get_by_project_id(project_id)
        planning = self.planning_repo.get_by_project_id(project_id)
        architecture = self.architecture_repo.get_by_project_id(project_id)

        if not research or not planning or not architecture:
            raise InvalidEvaluationOperationException(
                "Snapshots missing from repository."
            )

        r_snap = next(
            s
            for s in research.snapshots
            if s.metadata.id == evaluation.research_snapshot_id
        )
        p_snap = next(
            s
            for s in planning.snapshots
            if s.metadata.id == evaluation.planning_snapshot_id
        )
        a_snap = next(
            s
            for s in architecture.snapshots
            if s.metadata.id == evaluation.architecture_snapshot_id
        )

        new_findings: list[EvaluationFinding] = []

        # Audit ADR Traceability
        for adr in a_snap.decisions:
            if (
                not adr.supporting_evidence
                and not adr.related_research_findings
                and not adr.related_planning_tasks
            ):
                new_findings.append(
                    EvaluationFinding(
                        severity=FindingSeverity.BLOCKING,
                        category=FindingCategory.TRACEABILITY,
                        description=f"ADR {adr.title} lacks all upstream lineage.",
                        evidence=f"ADR ID: {adr.id} contains empty supporting_evidence, research_findings, and planning_tasks.",
                        recommendation="Map this design decision to the corresponding research evidence, finding, or planning task.",
                        traceability_links=[adr.id],
                    )
                )

        # Audit active drivers
        for drv in a_snap.drivers:
            all_findings = {f.id for f in r_snap.findings}
            for f_id in drv.source_finding_ids:
                if f_id not in all_findings:
                    new_findings.append(
                        EvaluationFinding(
                            severity=FindingSeverity.BLOCKING,
                            category=FindingCategory.TRACEABILITY,
                            description=f"Driver '{drv.name}' references invalid research finding.",
                            evidence=f"Driver ID: {drv.id} references non-existent finding ID: {f_id}.",
                            recommendation="Ensure driver points to a valid, approved research finding in the active baseline snapshot.",
                            traceability_links=[drv.id, f_id],
                        )
                    )

        # Filter out existing findings of the same description/evidence and extend
        evaluation.findings = [
            f for f in evaluation.findings if f.category != FindingCategory.TRACEABILITY
        ]
        evaluation.findings.extend(new_findings)
        self.repository.save(evaluation)
        return new_findings


class ArchitectureEvaluationService:
    """Evaluates component design boundaries and interface specifications."""

    def __init__(
        self,
        repository: EvaluationRepository,
        architecture_repo: ArchitectureRepository,
    ) -> None:
        self.repository = repository
        self.architecture_repo = architecture_repo

    def evaluate_architecture(self, project_id: UUID) -> list[EvaluationFinding]:
        """Audit component interface contracts and boundary completeness."""
        evaluation = self.repository.get_by_project_id(project_id)
        if not evaluation:
            raise EvaluationNotFoundException()
        _ensure_mutable(evaluation)

        architecture = self.architecture_repo.get_by_project_id(project_id)
        if not architecture:
            raise InvalidEvaluationOperationException("Architecture missing.")

        a_snap = next(
            s
            for s in architecture.snapshots
            if s.metadata.id == evaluation.architecture_snapshot_id
        )
        new_findings: list[EvaluationFinding] = []

        for comp in a_snap.components:
            if not comp.responsibilities:
                new_findings.append(
                    EvaluationFinding(
                        severity=FindingSeverity.WARNING,
                        category=FindingCategory.ARCHITECTURE,
                        description=f"Component '{comp.name}' lacks defined responsibilities.",
                        evidence=f"Component ID: {comp.id} contains empty responsibilities list.",
                        recommendation=f"Define explicit domain responsibilities for component '{comp.name}'.",
                        traceability_links=[comp.id],
                    )
                )

        evaluation.findings = [
            f for f in evaluation.findings if f.category != FindingCategory.ARCHITECTURE
        ]
        evaluation.findings.extend(new_findings)
        self.repository.save(evaluation)
        return new_findings


class RiskEvaluationService:
    """Audits identified risks and checks that critical threats contain mitigations."""

    def __init__(
        self,
        repository: EvaluationRepository,
        architecture_repo: ArchitectureRepository,
    ) -> None:
        self.repository = repository
        self.architecture_repo = architecture_repo

    def evaluate_risks(self, project_id: UUID) -> list[EvaluationFinding]:
        """Audit risk mitigation structures in technical design."""
        evaluation = self.repository.get_by_project_id(project_id)
        if not evaluation:
            raise EvaluationNotFoundException()
        _ensure_mutable(evaluation)

        architecture = self.architecture_repo.get_by_project_id(project_id)
        if not architecture:
            raise InvalidEvaluationOperationException("Architecture missing.")

        a_snap = next(
            s
            for s in architecture.snapshots
            if s.metadata.id == evaluation.architecture_snapshot_id
        )
        new_findings: list[EvaluationFinding] = []

        for risk in a_snap.risks:
            if risk.severity in ("critical", "high"):
                if not risk.mitigation or not risk.owner:
                    new_findings.append(
                        EvaluationFinding(
                            severity=FindingSeverity.BLOCKING,
                            category=FindingCategory.RISK,
                            description="Severe risk lacks mitigation or owner.",
                            evidence=f"Risk ID: {risk.id} has severity '{risk.severity}', mitigation: '{risk.mitigation}', owner: '{risk.owner}'.",
                            recommendation="Add an explicit mitigation strategy and assign a mitigation owner to the risk.",
                            traceability_links=[risk.id],
                        )
                    )

        evaluation.findings = [
            f for f in evaluation.findings if f.category != FindingCategory.RISK
        ]
        evaluation.findings.extend(new_findings)
        self.repository.save(evaluation)
        return new_findings


class QualityEvaluationService:
    """Reviews whether specified non-functional quality drivers contain implementing decisions."""

    def __init__(
        self,
        repository: EvaluationRepository,
        architecture_repo: ArchitectureRepository,
    ) -> None:
        self.repository = repository
        self.architecture_repo = architecture_repo

    def evaluate_quality_attributes(self, project_id: UUID) -> list[EvaluationFinding]:
        """Audit Quality Attributes for design conformance."""
        evaluation = self.repository.get_by_project_id(project_id)
        if not evaluation:
            raise EvaluationNotFoundException()
        _ensure_mutable(evaluation)

        architecture = self.architecture_repo.get_by_project_id(project_id)
        if not architecture:
            raise InvalidEvaluationOperationException("Architecture missing.")

        a_snap = next(
            s
            for s in architecture.snapshots
            if s.metadata.id == evaluation.architecture_snapshot_id
        )
        new_findings: list[EvaluationFinding] = []

        for qa in a_snap.quality_attributes:
            if not qa.related_adrs:
                new_findings.append(
                    EvaluationFinding(
                        severity=FindingSeverity.WARNING,
                        category=FindingCategory.QUALITY,
                        description=f"Quality attribute '{qa.name}' contains no implementing decisions.",
                        evidence=f"Quality Attribute ID: {qa.id} contains empty related_adrs.",
                        recommendation="Link this quality attribute to the relevant ADR decisions implementing it.",
                        traceability_links=[qa.id],
                    )
                )

        evaluation.findings = [
            f for f in evaluation.findings if f.category != FindingCategory.QUALITY
        ]
        evaluation.findings.extend(new_findings)
        self.repository.save(evaluation)
        return new_findings


class ReadinessEvaluationService:
    """Consolidates reviews and records formal readiness decisions."""

    def __init__(self, repository: EvaluationRepository) -> None:
        self.repository = repository

    def make_readiness_decision(
        self, project_id: UUID, ready: bool, justification: str
    ) -> ReadinessDecision:
        evaluation = self.repository.get_by_project_id(project_id)
        if not evaluation:
            raise EvaluationNotFoundException()
        _ensure_mutable(evaluation)

        decision = ReadinessDecision(ready=ready, justification=justification)
        evaluation.readiness_decision = decision
        self.repository.save(evaluation)
        return decision


class EvaluationSummaryService:
    """Orchestrates quality assessment workflow reviews and freezes immutable snapshots."""

    def __init__(self, repository: EvaluationRepository) -> None:
        self.repository = repository

    def submit_for_review(self, project_id: UUID) -> Evaluation:
        evaluation = self.repository.get_by_project_id(project_id)
        if not evaluation:
            raise EvaluationNotFoundException()

        if evaluation.status != ArtifactStatus.DRAFT:
            raise InvalidEvaluationOperationException("Only DRAFT can enter REVIEW.")

        evaluation.status = ArtifactStatus.REVIEW
        self.repository.save(evaluation)
        return evaluation

    def freeze_snapshot(self, project_id: UUID, synthesis: str) -> EvaluationSnapshot:
        """Create an immutable frozen snapshot of the evaluation pass."""
        evaluation = self.repository.get_by_project_id(project_id)
        if not evaluation:
            raise EvaluationNotFoundException()

        if evaluation.status != ArtifactStatus.REVIEW:
            raise InvalidEvaluationOperationException(
                "Cannot freeze without entering REVIEW state first."
            )

        if not evaluation.readiness_decision:
            raise InvalidEvaluationOperationException(
                "Cannot freeze evaluation without a recorded readiness decision."
            )

        blocking_count = sum(
            1 for f in evaluation.findings if f.severity == FindingSeverity.BLOCKING
        )
        satisfied_count = sum(1 for c in evaluation.coverage if c.status == "satisfied")
        partially_satisfied_count = sum(
            1 for c in evaluation.coverage if c.status == "partially_satisfied"
        )
        unsatisfied_count = sum(
            1 for c in evaluation.coverage if c.status == "unsatisfied"
        )

        summary = EvaluationSummary(
            synthesis=synthesis,
            total_findings=len(evaluation.findings),
            blocking_findings=blocking_count,
            satisfied_requirements=satisfied_count,
            partially_satisfied_requirements=partially_satisfied_count,
            unsatisfied_requirements=unsatisfied_count,
        )

        next_version = len(evaluation.snapshots) + 1
        snapshot = EvaluationSnapshot(
            metadata=ArtifactMetadata(
                version=next_version,
                status=ArtifactStatus.APPROVED,
            ),
            research_snapshot_id=evaluation.research_snapshot_id,
            planning_snapshot_id=evaluation.planning_snapshot_id,
            architecture_snapshot_id=evaluation.architecture_snapshot_id,
            findings=list(evaluation.findings),
            coverage=list(evaluation.coverage),
            readiness_decision=evaluation.readiness_decision,
            summary=summary,
        )

        evaluation.summary = summary
        evaluation.snapshots.append(snapshot)
        evaluation.status = ArtifactStatus.APPROVED
        self.repository.save(evaluation)
        return snapshot
