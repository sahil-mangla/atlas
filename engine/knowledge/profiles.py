from dataclasses import dataclass

from engine.domain.enums import KnowledgeCategory, WorkflowStage


@dataclass(frozen=True)
class KnowledgeRetrievalProfile:
    stage: WorkflowStage
    default_categories: tuple[KnowledgeCategory, ...]
    default_tags: tuple[str, ...] = ()
    max_entries: int = 20


RESEARCH_PROFILE = KnowledgeRetrievalProfile(WorkflowStage.RESEARCH, (KnowledgeCategory.LESSON_LEARNED, KnowledgeCategory.CONSTRAINT))
PLANNING_PROFILE = KnowledgeRetrievalProfile(WorkflowStage.PLANNING, (KnowledgeCategory.PATTERN, KnowledgeCategory.CONSTRAINT, KnowledgeCategory.DECISION_SUMMARY))
ARCHITECTURE_PROFILE = KnowledgeRetrievalProfile(WorkflowStage.ARCHITECTURE, (KnowledgeCategory.PATTERN, KnowledgeCategory.STANDARD, KnowledgeCategory.DECISION_SUMMARY, KnowledgeCategory.CONSTRAINT))
EVALUATION_PROFILE = KnowledgeRetrievalProfile(WorkflowStage.REVIEW, (KnowledgeCategory.LESSON_LEARNED, KnowledgeCategory.STANDARD, KnowledgeCategory.CONSTRAINT))
STAGE_PROFILES = {profile.stage: profile for profile in (RESEARCH_PROFILE, PLANNING_PROFILE, ARCHITECTURE_PROFILE, EVALUATION_PROFILE)}
