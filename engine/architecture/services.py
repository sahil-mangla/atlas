"""Services managing the Architecture subsystem lifecycle."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from engine.architecture.exceptions import (
    ArchitectureNotFoundException,
    InvalidArchitectureOperationException,
)
from engine.architecture.repository import ArchitectureRepository
from engine.domain.enums import ArchitectureStatus
from engine.domain.metadata import ArtifactMetadata, ArtifactStatus
from engine.domain.architecture import (
    Architecture,
    ArchitectureComponent,
    ArchitectureDriver,
    ArchitecturalDecision,
    InterfaceContract,
    Risk,
    Constraint,
    Assumption,
    QualityAttribute,
    ArchitectureSummary,
    ArchitectureSnapshot,
)
from engine.planning.repository import PlanningRepository
from engine.project.repository import ProjectRepository
from engine.research.repository import ResearchRepository


def _ensure_mutable(architecture: Architecture) -> None:
    """Ensure that the technical design is in a editable state."""
    if architecture.status in (ArchitectureStatus.APPROVED, ArchitectureStatus.ARCHIVED):
        raise InvalidArchitectureOperationException(
            "Cannot mutate architecture that is APPROVED or ARCHIVED."
        )


class ArchitectureInitializationService:
    """Handles creating the initial architecture design state for a project."""

    def __init__(
        self,
        project_repo: ProjectRepository,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
        architecture_repo: ArchitectureRepository,
    ) -> None:
        self.project_repo = project_repo
        self.research_repo = research_repo
        self.planning_repo = planning_repo
        self.architecture_repo = architecture_repo

    def initialize_architecture(
        self,
        project_id: UUID,
        research_snapshot_id: UUID,
        planning_snapshot_id: UUID,
    ) -> Architecture:
        """Create a new technical design context based on approved inputs."""
        if not self.project_repo.get_by_id(project_id):
            raise ArchitectureNotFoundException(
                f"Project {project_id} does not exist."
            )

        if self.architecture_repo.exists(project_id):
            raise InvalidArchitectureOperationException(
                f"Architecture already initialized for project {project_id}."
            )

        # Validate research snapshot is approved and exists
        research = self.research_repo.get_by_project_id(project_id)
        if not research:
            raise InvalidArchitectureOperationException(
                "Approved research not found for project."
            )
        research_snapshot = next(
            (s for s in research.snapshots if s.metadata.id == research_snapshot_id),
            None,
        )
        if not research_snapshot:
            raise InvalidArchitectureOperationException(
                f"Approved research snapshot {research_snapshot_id} not found."
            )

        # Validate planning snapshot is approved and exists
        planning = self.planning_repo.get_by_project_id(project_id)
        if not planning:
            raise InvalidArchitectureOperationException(
                "Approved planning not found for project."
            )
        planning_snapshot = next(
            (s for s in planning.snapshots if s.metadata.id == planning_snapshot_id),
            None,
        )
        if not planning_snapshot:
            raise InvalidArchitectureOperationException(
                f"Approved planning snapshot {planning_snapshot_id} not found."
            )

        architecture = Architecture(
            project_id=project_id, status=ArchitectureStatus.DRAFT
        )
        self.architecture_repo.save(architecture)
        return architecture


class ArchitectureCompositionService:
    """Handles adding general technical contexts, quality attributes, and drivers."""

    def __init__(
        self,
        repository: ArchitectureRepository,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
    ) -> None:
        self.repository = repository
        self.research_repo = research_repo
        self.planning_repo = planning_repo

    def set_design_summary(self, project_id: UUID, summary: str) -> None:
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)
        architecture.design_summary = summary
        self.repository.save(architecture)

    def add_constraint(
        self,
        project_id: UUID,
        description: str,
        impact: str,
        related_research_constraint_id: UUID | None = None,
    ) -> Constraint:
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)

        if related_research_constraint_id:
            research = self.research_repo.get_by_project_id(project_id)
            if not research:
                raise InvalidArchitectureOperationException("Research not found.")
            all_research_constraints = {
                c.id for s in research.snapshots for c in s.constraints
            }
            if related_research_constraint_id not in all_research_constraints:
                raise InvalidArchitectureOperationException(
                    "Referenced research constraint not found."
                )

        constraint = Constraint(
            description=description,
            impact=impact,
            related_research_constraint_id=related_research_constraint_id,
        )
        architecture.constraints.append(constraint)
        self.repository.save(architecture)
        return constraint

    def add_assumption(
        self,
        project_id: UUID,
        description: str,
        risk: str,
        related_research_assumption_id: UUID | None = None,
    ) -> Assumption:
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)

        if related_research_assumption_id:
            research = self.research_repo.get_by_project_id(project_id)
            if not research:
                raise InvalidArchitectureOperationException("Research not found.")
            all_research_assumptions = {
                a.id for s in research.snapshots for a in s.assumptions
            }
            if related_research_assumption_id not in all_research_assumptions:
                raise InvalidArchitectureOperationException(
                    "Referenced research assumption not found."
                )

        assumption = Assumption(
            description=description,
            risk=risk,
            related_research_assumption_id=related_research_assumption_id,
        )
        architecture.assumptions.append(assumption)
        self.repository.save(architecture)
        return assumption

    def add_quality_attribute(
        self, project_id: UUID, name: str, description: str, mitigation_strategy: str
    ) -> QualityAttribute:
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)

        qa = QualityAttribute(
            name=name,
            description=description,
            mitigation_strategy=mitigation_strategy,
        )
        architecture.quality_attributes.append(qa)
        self.repository.save(architecture)
        return qa

    def add_architecture_driver(
        self,
        project_id: UUID,
        name: str,
        description: str,
        driver_type: str,
        source_finding_ids: list[UUID],
        source_objective_ids: list[UUID],
    ) -> ArchitectureDriver:
        """Add an architecture driver, validating all linked research/planning source IDs."""
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)

        # Validate findings exist in research snapshots
        if source_finding_ids:
            research = self.research_repo.get_by_project_id(project_id)
            if not research:
                raise InvalidArchitectureOperationException("Research not found.")
            all_findings = {f.id for s in research.snapshots for f in s.findings}
            for f_id in source_finding_ids:
                if f_id not in all_findings:
                    raise InvalidArchitectureOperationException(
                        f"Referenced research finding {f_id} not found."
                    )

        # Validate planning objectives (Engineering Deliverables) exist
        if source_objective_ids:
            planning = self.planning_repo.get_by_project_id(project_id)
            if not planning:
                raise InvalidArchitectureOperationException("Planning not found.")
            all_deliverables = {
                d.id for s in planning.snapshots for d in s.scope_definition.deliverables
            }
            if planning.scope_definition:
                all_deliverables.update(
                    d.id for d in planning.scope_definition.deliverables
                )
            for o_id in source_objective_ids:
                if o_id not in all_deliverables:
                    raise InvalidArchitectureOperationException(
                        f"Referenced planning deliverable {o_id} not found."
                    )

        driver = ArchitectureDriver(
            name=name,
            description=description,
            driver_type=driver_type,
            source_finding_ids=source_finding_ids,
            source_objective_ids=source_objective_ids,
        )
        architecture.drivers.append(driver)
        self.repository.save(architecture)
        return driver


class ArchitecturalDecisionService:
    """Handles adding and updating Architectural Decision Records (ADRs)."""

    def __init__(
        self,
        repository: ArchitectureRepository,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
    ) -> None:
        self.repository = repository
        self.research_repo = research_repo
        self.planning_repo = planning_repo

    def add_adr(
        self,
        project_id: UUID,
        title: str,
        context: str,
        problem_statement: str,
        decision: str,
        rationale: str,
        consequences: str = "",
        alternatives_considered: list[str] | None = None,
        reasons_rejected: list[str] | None = None,
        trade_offs: list[str] | None = None,
        related_constraints: list[UUID] | None = None,
        related_assumptions: list[UUID] | None = None,
        supporting_evidence: list[UUID] | None = None,
        related_planning_tasks: list[UUID] | None = None,
        related_research_findings: list[UUID] | None = None,
        traceability_links: list[str] | None = None,
    ) -> ArchitecturalDecision:
        """Register an ADR, validating all referenced inputs exist."""
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)

        # Validate local constraints
        local_constraints = {c.id for c in architecture.constraints}
        for c_id in related_constraints or []:
            if c_id not in local_constraints:
                raise InvalidArchitectureOperationException(
                    f"Constraint {c_id} not defined in active architecture."
                )

        # Validate local assumptions
        local_assumptions = {a.id for a in architecture.assumptions}
        for a_id in related_assumptions or []:
            if a_id not in local_assumptions:
                raise InvalidArchitectureOperationException(
                    f"Assumption {a_id} not defined in active architecture."
                )

        # Validate research evidence and findings
        if supporting_evidence or related_research_findings:
            research = self.research_repo.get_by_project_id(project_id)
            if not research:
                raise InvalidArchitectureOperationException("Research not found.")

            if supporting_evidence:
                all_evidence = {e.id for s in research.snapshots for e in s.evidence}
                for e_id in supporting_evidence:
                    if e_id not in all_evidence:
                        raise InvalidArchitectureOperationException(
                            f"Evidence {e_id} not found in research."
                        )

            if related_research_findings:
                all_findings = {f.id for s in research.snapshots for f in s.findings}
                for f_id in related_research_findings:
                    if f_id not in all_findings:
                        raise InvalidArchitectureOperationException(
                            f"Finding {f_id} not found in research."
                        )

        # Validate planning tasks
        if related_planning_tasks:
            planning = self.planning_repo.get_by_project_id(project_id)
            if not planning:
                raise InvalidArchitectureOperationException("Planning not found.")
            all_tasks = set()
            for s in planning.snapshots:
                for m in s.milestones:
                    for e in m.epics:
                        for t in e.tasks:
                            all_tasks.add(t.id)
                            for st in t.subtasks:
                                all_tasks.add(st.id)
            for m in planning.milestones:
                for e in m.epics:
                    for t in e.tasks:
                        all_tasks.add(t.id)
                        for st in t.subtasks:
                            all_tasks.add(st.id)
            for t_id in related_planning_tasks:
                if t_id not in all_tasks:
                    raise InvalidArchitectureOperationException(
                        f"Planning task {t_id} not found."
                    )

        adr = ArchitecturalDecision(
            title=title,
            context=context,
            problem_statement=problem_statement,
            decision=decision,
            rationale=rationale,
            consequences=consequences,
            alternatives_considered=alternatives_considered or [],
            reasons_rejected=reasons_rejected or [],
            trade_offs=trade_offs or [],
            related_constraints=related_constraints or [],
            related_assumptions=related_assumptions or [],
            supporting_evidence=supporting_evidence or [],
            related_planning_tasks=related_planning_tasks or [],
            related_research_findings=related_research_findings or [],
            traceability_links=traceability_links or [],
        )
        architecture.decisions.append(adr)
        self.repository.save(architecture)
        return adr


class ComponentModelService:
    """Handles component definitions, dependencies, cycle checking, and linkings."""

    def __init__(self, repository: ArchitectureRepository) -> None:
        self.repository = repository

    def add_component(
        self,
        project_id: UUID,
        name: str,
        responsibilities: list[str],
        owned_data: list[str],
        external_dependencies: list[str],
    ) -> ArchitectureComponent:
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)

        component = ArchitectureComponent(
            name=name,
            responsibilities=responsibilities,
            owned_data=owned_data,
            external_dependencies=external_dependencies,
        )
        architecture.components.append(component)
        self.repository.save(architecture)
        return component

    def add_internal_dependency(
        self, project_id: UUID, component_id: UUID, depends_on_id: UUID
    ) -> None:
        """Link one internal component dependency to another, verifying no cycles."""
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)

        comp = next((c for c in architecture.components if c.id == component_id), None)
        dep = next((c for c in architecture.components if c.id == depends_on_id), None)
        if not comp or not dep:
            raise InvalidArchitectureOperationException("Component not found.")

        if component_id == depends_on_id:
            raise InvalidArchitectureOperationException(
                "Component cannot depend on itself."
            )

        # Check for cycles
        graph: dict[UUID, list[UUID]] = {c.id: list(c.internal_dependencies) for c in architecture.components}
        graph[component_id].append(depends_on_id)

        visited: set[UUID] = set()
        rec_stack: set[UUID] = set()

        def dfs(node: UUID) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited and dfs(node):
                raise InvalidArchitectureOperationException(
                    "Dependency cycle detected in architecture components."
                )

        comp.internal_dependencies.append(depends_on_id)
        self.repository.save(architecture)

    def associate_adr_to_component(
        self, project_id: UUID, component_id: UUID, adr_id: UUID
    ) -> None:
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)

        comp = next((c for c in architecture.components if c.id == component_id), None)
        if not comp:
            raise InvalidArchitectureOperationException("Component not found.")

        if not any(adr.id == adr_id for adr in architecture.decisions):
            raise InvalidArchitectureOperationException("ADR not found.")

        if adr_id not in comp.related_adrs:
            comp.related_adrs.append(adr_id)
            self.repository.save(architecture)

    def associate_risk_to_component(
        self, project_id: UUID, component_id: UUID, risk_id: UUID
    ) -> None:
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)

        comp = next((c for c in architecture.components if c.id == component_id), None)
        if not comp:
            raise InvalidArchitectureOperationException("Component not found.")

        if not any(risk.id == risk_id for risk in architecture.risks):
            raise InvalidArchitectureOperationException("Risk not found.")

        if risk_id not in comp.related_risks:
            comp.related_risks.append(risk_id)
            self.repository.save(architecture)


class InterfaceContractService:
    """Handles declaring public interface contracts on components."""

    def __init__(self, repository: ArchitectureRepository) -> None:
        self.repository = repository

    def add_interface_contract(
        self,
        project_id: UUID,
        component_id: UUID,
        name: str,
        description: str,
        protocol: str,
        input_schema: str,
        output_schema: str,
    ) -> InterfaceContract:
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)

        comp = next((c for c in architecture.components if c.id == component_id), None)
        if not comp:
            raise InvalidArchitectureOperationException("Component not found.")

        contract = InterfaceContract(
            name=name,
            description=description,
            protocol=protocol,
            input_schema=input_schema,
            output_schema=output_schema,
        )
        comp.public_interfaces.append(contract)
        self.repository.save(architecture)
        return contract


class RiskAnalysisService:
    """Handles registering and assigning technical risks to ADR owners."""

    def __init__(self, repository: ArchitectureRepository) -> None:
        self.repository = repository

    def register_risk(
        self,
        project_id: UUID,
        description: str,
        severity: str,
        likelihood: str,
        impact: str,
        mitigation: str,
        owner: str,
        related_decision_id: UUID | None = None,
    ) -> Risk:
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()
        _ensure_mutable(architecture)

        if related_decision_id:
            if not any(adr.id == related_decision_id for adr in architecture.decisions):
                raise InvalidArchitectureOperationException(
                    "Referenced ADR not found."
                )

        risk = Risk(
            description=description,
            severity=severity,
            likelihood=likelihood,
            impact=impact,
            mitigation=mitigation,
            owner=owner,
            related_decision_id=related_decision_id,
        )
        architecture.risks.append(risk)
        self.repository.save(architecture)
        return risk


class ArchitectureSummaryService:
    """Handles advancing technical review workflows and freezing snapshot baselines."""

    def __init__(
        self,
        repository: ArchitectureRepository,
        research_repo: ResearchRepository,
        planning_repo: PlanningRepository,
    ) -> None:
        self.repository = repository
        self.research_repo = research_repo
        self.planning_repo = planning_repo

    def submit_for_review(self, project_id: UUID) -> Architecture:
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()

        if architecture.status != ArchitectureStatus.DRAFT:
            raise InvalidArchitectureOperationException("Only DRAFT can enter REVIEW.")

        architecture.status = ArchitectureStatus.REVIEW
        self.repository.save(architecture)
        return architecture

    def freeze_snapshot(
        self,
        project_id: UUID,
        planning_snapshot_id: UUID,
        research_snapshot_id: UUID,
        synthesis: str,
    ) -> ArchitectureSnapshot:
        """Create an immutable snapshot of the active technical design state."""
        architecture = self.repository.get_by_project_id(project_id)
        if not architecture:
            raise ArchitectureNotFoundException()

        if architecture.status != ArchitectureStatus.REVIEW:
            raise InvalidArchitectureOperationException(
                "Cannot freeze without entering REVIEW state first."
            )

        # Validate inputs exist in external aggregates
        research = self.research_repo.get_by_project_id(project_id)
        if not research or not any(
            s.metadata.id == research_snapshot_id for s in research.snapshots
        ):
            raise InvalidArchitectureOperationException(
                "Baseline ResearchSnapshot not found or not approved."
            )

        planning = self.planning_repo.get_by_project_id(project_id)
        if not planning or not any(
            s.metadata.id == planning_snapshot_id for s in planning.snapshots
        ):
            raise InvalidArchitectureOperationException(
                "Baseline PlanningSnapshot not found or not approved."
            )

        summary = ArchitectureSummary(
            synthesis=synthesis,
            total_components=len(architecture.components),
            total_adrs=len(architecture.decisions),
            total_risks=len(architecture.risks),
        )

        next_version = len(architecture.snapshots) + 1
        snapshot = ArchitectureSnapshot(
            metadata=ArtifactMetadata(
                version=next_version,
                status=ArtifactStatus.APPROVED,
            ),
            planning_snapshot_id=planning_snapshot_id,
            research_snapshot_id=research_snapshot_id,
            drivers=list(architecture.drivers),
            components=list(architecture.components),
            decisions=list(architecture.decisions),
            risks=list(architecture.risks),
            constraints=list(architecture.constraints),
            assumptions=list(architecture.assumptions),
            quality_attributes=list(architecture.quality_attributes),
            summary=summary,
        )

        architecture.summary = summary
        architecture.snapshots.append(snapshot)
        architecture.status = ArchitectureStatus.APPROVED
        self.repository.save(architecture)
        return snapshot
