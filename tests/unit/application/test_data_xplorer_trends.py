"""Contratos do build estável Data Xplorer, sem chamadas externas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prometeus.application.evidence_features import EvidenceFeatureExtractor
from prometeus.application.plan_course_research import CourseResearchPlanner
from prometeus.application.skill_registry import SkillRegistry
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseUnderstanding, PlannedToolCall
from prometeus.infrastructure.apify.normalizers import normalize_trends
from prometeus.infrastructure.apify.registry import ActorConfigurationError, ApifyActorRegistry
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


def settings() -> AppSettings:
    return AppSettings(
        _env_file=None,
        APIFY_REQUIRED_SOURCES="google_trends",
        APIFY_ACTOR_GOOGLE_TRENDS="data_xplorer/google-trends-fast-scraper@2.10.2",
    )


def call(**updates: object) -> PlannedToolCall:
    values = {
        "id": "trends",
        "capability": "google_trends",
        "query": "curso LGPD",
        "rationale": "Interesse relativo ao longo do tempo",
        "parameters": {"geo": "BR", "time_range": "today 12-m"},
    }
    values.update(updates)
    return PlannedToolCall.model_validate(values)


def test_data_xplorer_build_uses_verified_keyword_mode_contract() -> None:
    registry = ApifyActorRegistry.from_settings(settings())
    assert registry.require("google_trends").build == "2.10.2"
    assert registry.build_input(call()) == {
        "mode": "keyword",
        "keyword": "curso LGPD",
        "predefinedTimeframe": "today 12-m",
        "geo": "BR",
        "fetchRegionalData": False,
        "proxyConfiguration": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
    }


def test_data_xplorer_rejects_unexpanded_terms_instead_of_losing_keywords() -> None:
    registry = ApifyActorRegistry.from_settings(settings())
    with pytest.raises(ActorConfigurationError, match="um termo"):
        registry.build_input(call(parameters={"search_terms": ["curso LGPD", "governança IA"]}))


def test_data_xplorer_normalizes_entire_real_series_including_zero_and_partial_tail() -> None:
    raw = json.loads(
        Path("tests/fixtures/apify/data_xplorer_trends_2_10_2.json").read_text(encoding="utf-8")
    )[0]
    raw["future_field"] = {"nested": ["keep", 0, False]}
    obs = normalize_trends(raw)
    assert obs.term == "curso governança IA"
    assert obs.total_points == 53
    assert obs.points[0].time == "2025-11-09"
    assert obs.points[0].value == [0]
    assert obs.points[0].has_data is True
    assert obs.points[-1].time == "2026-11-08"
    assert obs.points[-1].is_partial is True
    assert obs.partial_points == 1
    assert obs.valid_points == 53
    assert obs.source_url == raw["trends_url"]
    assert obs.raw_payload == raw
    metrics = EvidenceFeatureExtractor._trends_metrics(raw)
    assert metrics["average_interest"] == round(217 / 52, 4)
    assert "search_volume" not in metrics


@pytest.mark.parametrize("alias", ["searchTerm", "keyword"])
def test_trends_term_alias_and_zero_are_observed_even_with_no_positive_interest(alias: str) -> None:
    raw = {alias: "termo", "timeline_data": {"termo": {"2026-01-01": 0}}}
    obs = normalize_trends(raw)
    assert obs.term == "termo"
    assert obs.points[0].value == [0]
    assert EvidenceFeatureExtractor._trends_metrics(raw) == {"average_interest": 0.0}


def test_nested_legacy_timeline_uses_same_canonical_metrics_and_discards_partial_for_metric() -> None:
    raw = {
        "searchTerm": "curso",
        "interestOverTime": {"timelineData": [
            {"time": "1", "value": [0], "hasData": [True]},
            {"time": "2", "value": [20], "hasData": True},
            {"time": "3", "value": [100], "isPartial": [True]},
        ]},
    }
    assert len(normalize_trends(raw).points) == 3
    assert EvidenceFeatureExtractor._trends_metrics(raw) == {"average_interest": 10.0}


@pytest.mark.asyncio
async def test_planner_expands_all_keywords_stably_and_preserves_dependencies_and_questions() -> None:
    terms = [f"curso tema {idx}" for idx in range(7)]
    body = {"questions": [{"id": "q", "question": "Há interesse?"}], "tool_calls": [
        call(parameters={"search_terms": terms, "time_range": "today 12-m"}, question_ids=["q"]).model_dump(),
        call(id="dependent", query="curso adicional", parameters={"depends_on": ["trends"]}).model_dump(),
    ]}
    planner = CourseResearchPlanner(
        FakeGenerativeModel(canned_text=json.dumps(body)), SkillRegistry("skills"), settings()
    )
    understanding = CourseUnderstanding(analysis_id="test", course_title="LGPD")
    plan = await planner.plan(understanding)
    repeated = await planner.plan(understanding)
    expanded = [item for item in plan.tool_calls if item.id != "dependent"]
    assert [item.query for item in expanded] == terms
    assert [item.id for item in plan.tool_calls] == [item.id for item in repeated.tool_calls]
    assert len({item.id for item in plan.tool_calls}) == 8
    assert all(item.question_ids == ["q"] for item in expanded)
    assert all(item.required for item in expanded)
    assert all(item.parameters["search_terms"] == [item.query] for item in expanded)
    dependent = next(item for item in plan.tool_calls if item.id == "dependent")
    assert dependent.parameters["depends_on"] == [item.id for item in expanded]
    registry = ApifyActorRegistry.from_settings(settings())
    assert [registry.build_input(item)["keyword"] for item in expanded] == terms
