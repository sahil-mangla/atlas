"""Architecture subsystem for the ATLAS platform."""

from engine.architecture.exceptions import (
    ArchitectureException,
    ArchitectureNotFoundException,
    InvalidArchitectureException,
    InvalidArchitectureOperationException,
)
from engine.architecture.repository import ArchitectureRepository
from engine.architecture.services import (
    ArchitecturalDecisionService,
    ArchitectureCompositionService,
    ArchitectureInitializationService,
    ArchitectureSummaryService,
    ComponentModelService,
    InterfaceContractService,
    RiskAnalysisService,
)

__all__ = [
    "ArchitectureException",
    "ArchitectureNotFoundException",
    "InvalidArchitectureException",
    "InvalidArchitectureOperationException",
    "ArchitectureRepository",
    "ArchitectureInitializationService",
    "ArchitectureCompositionService",
    "ArchitecturalDecisionService",
    "ComponentModelService",
    "InterfaceContractService",
    "RiskAnalysisService",
    "ArchitectureSummaryService",
]
