from engine.domain.enums import WorkflowStage
from engine.knowledge.profiles import STAGE_PROFILES


def test_stage_profiles_completeness() -> None:
    expected_stages = {
        WorkflowStage.RESEARCH,
        WorkflowStage.PLANNING,
        WorkflowStage.ARCHITECTURE,
        WorkflowStage.REVIEW,
    }
    for stage in expected_stages:
        assert stage in STAGE_PROFILES, f"Missing profile for {stage}"


def test_profile_attributes() -> None:
    profile = STAGE_PROFILES[WorkflowStage.RESEARCH]
    assert profile.default_categories
    assert isinstance(profile.max_entries, int)
