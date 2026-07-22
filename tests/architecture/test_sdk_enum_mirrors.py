"""RC-007 regression: every SDK-boundary enum mirror in ``atlas.types`` /
``atlas.commands`` must have exactly the same members as the
``engine.domain.enums`` type it stands in for.

Before this fix, ``atlas.types.ProposalStatus`` was missing two members
(``pending_review``, ``expired``) that ``engine.domain.enums.ProposalStatus``
actually has. Nothing currently assigns those two engine-side, so it was a
latent bug rather than a live crash -- but the moment engine code starts
using them, converting an engine ``ProposalStatus`` to the SDK-facing one
(as ``PresentationCapability``/``WorkflowExecutionCapability`` already do
for other enums) would raise ``ValueError``. These mirrors exist precisely
so ``clients/`` never has to import ``engine`` directly (see
``tests/test_clients/test_imports.py``); a mirror that's silently missing
members defeats that purpose.
"""

import atlas.types as atlas_types
import engine.domain.enums as engine_enums

# (atlas.types member name, engine.domain.enums member name) for every pair
# that is meant to mirror each other one-to-one.
_MIRRORED_ENUM_PAIRS = (
    ("ProjectStatus", "ProjectStatus"),
    ("WorkflowStage", "WorkflowStage"),
    ("ProposalStatus", "ProposalStatus"),
    ("EvaluationStatus", "EvaluationStatus"),
    ("ProposalDecision", "ProposalDecision"),
    ("KnowledgeActorType", "KnowledgeActorType"),
    ("KnowledgeCandidateStatus", "KnowledgeCandidateStatus"),
)


def test_every_declared_mirror_pair_actually_exists() -> None:
    """Guard the table above itself against a typo'd or renamed member."""
    for atlas_name, engine_name in _MIRRORED_ENUM_PAIRS:
        assert hasattr(atlas_types, atlas_name), f"atlas.types.{atlas_name} missing"
        assert hasattr(engine_enums, engine_name), (
            f"engine.domain.enums.{engine_name} missing"
        )


def test_sdk_enum_mirrors_have_identical_members() -> None:
    for atlas_name, engine_name in _MIRRORED_ENUM_PAIRS:
        atlas_enum = getattr(atlas_types, atlas_name)
        engine_enum = getattr(engine_enums, engine_name)
        atlas_values = {member.value for member in atlas_enum}
        engine_values = {member.value for member in engine_enum}
        assert atlas_values == engine_values, (
            f"atlas.types.{atlas_name} {sorted(atlas_values)} does not match "
            f"engine.domain.enums.{engine_name} {sorted(engine_values)}"
        )
