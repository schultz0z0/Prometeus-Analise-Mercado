"""Testes unitários para modelos de dados e contratos de features de scoring."""

from prometeus.domain.analyses import AnalysisRecommendation
from prometeus.domain.scoring.models import (
    GateEvaluation,
    PillarScore,
    PillarType,
    ScoringResult,
)


def test_pillar_types_enum() -> None:
    assert PillarType.INTERNAL_HISTORY == "internal_history"
    assert PillarType.PAID_COMPETITION == "paid_competition"
    assert PillarType.SEARCH_AND_MEDIA == "search_and_media"
    assert PillarType.EMPLOYABILITY == "employability"
    assert PillarType.SYLLABUS_FIT == "syllabus_fit"
    assert PillarType.PRICING == "pricing"


def test_pillar_score_weighted_calculations() -> None:
    p_present = PillarScore(
        pillar_id="internal_history",
        raw_score=80.0,
        weight=0.20,
        confidence=0.90,
        is_present=True,
    )
    assert p_present.weighted_score == 16.0  # 80.0 * 0.20
    assert p_present.weighted_confidence == 0.18  # 0.90 * 0.20

    p_absent = PillarScore(
        pillar_id="pricing",
        raw_score=0.0,
        weight=0.10,
        confidence=0.0,
        is_present=False,
    )
    assert p_absent.weighted_score == 0.0
    assert p_absent.weighted_confidence == 0.0


def test_scoring_result_instantiation() -> None:
    gate_eval = GateEvaluation(
        recommendation=AnalysisRecommendation.APPROVED,
        passed_gates=True,
        viability_score=82.5,
        coverage_score=1.0,
        confidence_score=0.88,
    )

    res = ScoringResult.create(
        analysis_id="an-001",
        profile_id="default-v1",
        viability_score=82.555,
        coverage_score=1.0,
        confidence_score=0.884,
        partial_score=82.555,
        recommendation=AnalysisRecommendation.APPROVED,
        pillar_scores={},
        gate_details=gate_eval,
        is_experimental=True,
    )

    assert res.analysis_id == "an-001"
    assert res.viability_score == 82.56
    assert res.confidence_score == 0.884
    assert res.recommendation == AnalysisRecommendation.APPROVED
    assert res.is_experimental is True
