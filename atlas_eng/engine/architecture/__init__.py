"""Architecture subsystem for the ATLAS platform."""

from atlas_eng.engine.architecture.exceptions import (
    ArchitectureException,
    ArchitectureNotFoundException,
    InvalidArchitectureException,
    InvalidArchitectureOperationException,
)
from atlas_eng.engine.architecture.repository import ArchitectureRepository
from atlas_eng.engine.architecture.services import (
    ArchitecturalDecisionService,
    ArchitectureCompositionService,
    ArchitectureInitializationService,
    ArchitectureSummaryService,
    ComponentModelService,
    InterfaceContractService,
    RiskAnalysisService,
)

__all__ = [
    "ArchitecturalDecisionService",
    "ArchitectureCompositionService",
    "ArchitectureException",
    "ArchitectureInitializationService",
    "ArchitectureNotFoundException",
    "ArchitectureRepository",
    "ArchitectureSummaryService",
    "ComponentModelService",
    "InterfaceContractService",
    "InvalidArchitectureException",
    "InvalidArchitectureOperationException",
    "RiskAnalysisService",
]
