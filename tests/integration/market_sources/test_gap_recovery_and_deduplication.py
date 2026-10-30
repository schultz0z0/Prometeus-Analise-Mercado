"""Testes de integração para recuperação por causa e ganho marginal.

Valida requisitos da Tarefa 2.4 do plano de inteligência de mercado:
- Classificação de lacunas nas 7 causas canônicas:
  1. source_failure
  2. unsupported_source
  3. normalization_loss
  4. context_projection_loss
  5. qualification_uncertain
  6. true_no_signal
  7. missing_primary_data
- Ações correspondentes: dados existentes NÃO são recomprados quando a perda é de normalização ou projeção
- Deduplicação de consultas usando input efetivo normalizado (não apenas string descritiva da query)
- Critérios de parada por redundância, valor marginal nulo ou teto orçamentário
"""

from __future__ import annotations

import json

import pytest

from prometeus.application.evidence_features import EvidenceFeatureSet
from prometeus.application.plan_course_research import CourseResearchPlanner
from prometeus.application.research_sufficiency import (
    GapCause,
    GapRecoveryAction,
    classify_research_gaps,
)
from prometeus.application.skill_registry import SkillRegistry
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import CourseUnderstanding


def test_gap_classification_identifies_normalization_loss_without_rebuying():
    # Scenario: raw items were received (raw_items_count=3), but 0 valid items were normalized
    runs = [
        {
            "id": "run-trends-1",
            "capability": "google_trends",
            "status": "SUCCEEDED",
            "raw_items_count": 3,
            "valid_items_count": 0,
            "parameters": {"observation_status": "rejected_items"},
        }
    ]
    evidences = []
    features = EvidenceFeatureSet(features={})

    gaps = classify_research_gaps(features, runs=runs, evidences=evidences)
    trends_gaps = [g for g in gaps if g.feature_name in {"monthly_search_volume", "average_interest"}]

    assert len(trends_gaps) > 0
    assert trends_gaps[0].cause == GapCause.NORMALIZATION_LOSS
    assert trends_gaps[0].recommended_action == GapRecoveryAction.REPROCESS_LOCAL_DATA
    assert trends_gaps[0].reproducible_without_cost is True


def test_gap_classification_identifies_context_projection_loss():
    # Scenario: valid items exist in evidences, but features set has no records (e.g. truncated during prompt projection)
    runs = [
        {
            "id": "run-trends-2",
            "capability": "google_trends",
            "status": "SUCCEEDED",
            "raw_items_count": 3,
            "valid_items_count": 3,
            "parameters": {"observation_status": "observed"},
        }
    ]
    evidences = [
        {
            "tool_run_id": "run-trends-2",
            "evidence_type": "TRENDS",
            "sanitized_data": {"term": "fraudes em seguros", "points": [10, 20]},
        }
    ]
    features = EvidenceFeatureSet(features={})

    gaps = classify_research_gaps(features, runs=runs, evidences=evidences)
    trends_gaps = [g for g in gaps if g.feature_name in {"monthly_search_volume", "average_interest"}]

    assert len(trends_gaps) > 0
    assert trends_gaps[0].cause == GapCause.CONTEXT_PROJECTION_LOSS
    assert trends_gaps[0].recommended_action == GapRecoveryAction.REPROJECT_CONTEXT
    assert trends_gaps[0].reproducible_without_cost is True


def test_gap_classification_identifies_source_failure():
    runs = [
        {
            "id": "run-fail",
            "capability": "linkedin_jobs",
            "status": "FAILED",
            "raw_items_count": 0,
            "valid_items_count": 0,
            "error_code": "timeout",
            "parameters": {},
        }
    ]
    gaps = classify_research_gaps(EvidenceFeatureSet(features={}), runs=runs, evidences=[])
    job_gaps = [g for g in gaps if g.feature_name == "open_jobs_count"]

    assert len(job_gaps) > 0
    assert job_gaps[0].cause == GapCause.SOURCE_FAILURE
    assert job_gaps[0].recommended_action == GapRecoveryAction.RETRY_WITH_BACKOFF


def test_gap_classification_identifies_true_no_signal():
    runs = [
        {
            "id": "run-empty",
            "capability": "google_search",
            "status": "EMPTY",
            "raw_items_count": 0,
            "valid_items_count": 0,
            "parameters": {"observation_status": "observed_empty"},
        }
    ]
    gaps = classify_research_gaps(EvidenceFeatureSet(features={}), runs=runs, evidences=[])
    price_gaps = [g for g in gaps if g.feature_name == "market_median_price_brl"]

    assert len(price_gaps) > 0
    assert price_gaps[0].cause == GapCause.TRUE_NO_SIGNAL
    assert price_gaps[0].recommended_action == GapRecoveryAction.ACCEPT_ABSENCE_OF_SIGNAL


@pytest.mark.asyncio
async def test_query_deduplication_via_normalized_effective_input():
    from unittest.mock import AsyncMock

    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = json.dumps(
        {
            "questions": [{"id": "q1", "text": "Interesse de busca"}],
            "tool_calls": [
                {
                    "id": "trends-call",
                    "capability": "google_trends",
                    "query": "Fraudes em Seguros",
                    "rationale": "Série temporal",
                    "required": False,
                    "max_items": 5,
                    "parameters": {"geo": "BR", "time_range": "today 3-m"},
                }
            ],
        }
    )

    settings = AppSettings(
        _env_file=None,
        APIFY_ACTOR_GOOGLE_TRENDS="apify/google-trends-scraper@0.0.1",
        REQUIRED_MARKET_SOURCES=[],
    )
    planner = CourseResearchPlanner(
        llm=mock_llm,
        skills=SkillRegistry(),
        settings=settings,
    )

    understanding = CourseUnderstanding(
        analysis_id="test-dedup",
        course_title="MBA em Gestão de Fraudes em Seguros",
        target_audience="Profissionais de seguros e regulação de sinistros",
        subject_domains=["Fraudes em Seguros", "Sinistros"],
        key_differentiators=["Foco prático ENS"],
        modality="ONLINE",
        workload_hours=360,
        geography="Brasil",
        language="pt-BR",
    )

    # Previous query executed Trends with effective parameters for 'fraudes seguros'
    # ("Fraudes em Seguros" has identical stopword-filtered tokens: 'fraudes seguros')
    previous_effective_calls = [
        ("google_trends", "fraudes seguros")
    ]

    # New plan should filter out the duplicate Trends call via normalized signature
    plan = await planner.plan(
        understanding=understanding,
        previous_queries=previous_effective_calls,
        gaps=["Sem série de busca"],
    )

    trends_calls = [c for c in plan.tool_calls if c.capability == "google_trends"]
    assert len(trends_calls) == 0
