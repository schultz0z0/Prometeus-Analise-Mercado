"""Contracts for the guidance runtime actually loads, without evaluating an LLM."""

from pathlib import Path

import pytest
import yaml

from prometeus.application.skill_registry import SkillRegistry, SkillRegistryError
from prometeus.application.tool_capabilities import CAPABILITY_CONTRACTS
from prometeus.domain.ports.decision_model import DecisionPack
from prometeus.infrastructure.apify.registry import CAPABILITY_DEFINITIONS


@pytest.mark.parametrize("stage", ["internal_comparables", "pricing_extraction"])
def test_new_analytical_stages_resolve_versioned_allowlisted_guidance(stage):
    skills = SkillRegistry().for_stage(stage)
    assert skills
    assert all(skill.name in SkillRegistry().allowed_names for skill in skills)
    assert all(len(skill.content_hash) == 64 for skill in skills)
    assert len({skill.name for skill in skills}) == len(skills)


def test_every_executable_source_has_a_complete_review_and_recovery_contract():
    assert set(CAPABILITY_CONTRACTS) == set(CAPABILITY_DEFINITIONS)
    required_fields = {
        "purpose",
        "query_strategy",
        "evidence_expected",
        "limitations",
        "evidence_use",
        "acceptance",
        "rejection",
        "diagnostic",
        "recovery",
        "sample_policy",
    }
    for name, guidance in CAPABILITY_CONTRACTS.items():
        assert required_fields <= guidance.keys(), name
        assert all(
            isinstance(guidance[key], str) and guidance[key].strip() for key in required_fields
        )


def test_guidance_stages_still_reject_arbitrary_paths():
    with pytest.raises(SkillRegistryError):
        SkillRegistry().for_stage("../../credentials")


@pytest.mark.parametrize("name", ["market-relevance-v1", "syllabus-fit-v1", "comparable-fit-v1"])
def test_updated_decision_packs_keep_typed_judgment_contracts(name):
    payload = yaml.safe_load(Path(f"config/decision-packs/{name}.yaml").read_text(encoding="utf-8"))
    pack = DecisionPack.model_validate(payload)
    assert pack.pack_id == name
    assert pack.version == "2.0.0"
    assert 0 < pack.review_threshold <= 1
    if pack.decision_type.value == "CHOICE":
        assert set(pack.options) == set(pack.rubric)
    else:
        assert pack.min_score == 0 and pack.max_score == 100
