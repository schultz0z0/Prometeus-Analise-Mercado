from pathlib import Path

import pytest

from prometeus.application.skill_registry import SkillRegistry, SkillRegistryError

EXPECTED_SKILLS = {
    "understanding-course-proposals",
    "planning-market-research",
    "reviewing-market-evidence",
    "auditing-course-curriculum",
    "building-course-offers",
}


def test_registry_loads_versioned_allowlisted_domain_skills() -> None:
    registry = SkillRegistry(Path("skills"))

    loaded = registry.load_all()

    assert set(loaded) == EXPECTED_SKILLS
    for skill in loaded.values():
        assert skill.version
        assert len(skill.content_hash) == 64
        assert skill.description.startswith("Use when")


def test_registry_selects_skills_by_workflow_stage() -> None:
    registry = SkillRegistry(Path("skills"))

    assert [s.name for s in registry.for_stage("course_understanding")] == [
        "understanding-course-proposals"
    ]
    assert [s.name for s in registry.for_stage("research_planning")] == ["planning-market-research"]
    assert [s.name for s in registry.for_stage("dossier_synthesis")] == [
        "reviewing-market-evidence",
        "building-course-offers",
    ]


def test_registry_rejects_arbitrary_skill_path() -> None:
    registry = SkillRegistry(Path("skills"))

    with pytest.raises(SkillRegistryError, match="allowlist"):
        registry.get("../secrets")
