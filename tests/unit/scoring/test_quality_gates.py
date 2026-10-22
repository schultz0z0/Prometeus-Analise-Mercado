"""Testes unitários para QualityGateEvaluator e precedência ordenada de recomendações."""

from prometeus.domain.analyses import AnalysisRecommendation
from prometeus.domain.configuration import (
    ScoringGates,
    ScoringProfileConfig,
    ScoringThresholds,
)
from prometeus.domain.scoring.models import PillarScore, PillarType
from prometeus.domain.scoring.quality_gates import QualityGateEvaluator


def create_test_profile(
    min_cov: float = 0.80,
    min_conf: float = 0.75,
    th_app: float = 75.0,
    th_adj: float = 60.0,
    margin: float = 3.0,
    required: list[str] | None = None,
) -> ScoringProfileConfig:
    return ScoringProfileConfig(
        profile_id="test-profile",
        weights={
            "internal_history": 0.20,
            "paid_competition": 0.20,
            "search_and_media": 0.20,
            "employability": 0.15,
            "syllabus_fit": 0.15,
            "pricing": 0.10,
        },
        gates=ScoringGates(minimum_coverage=min_cov, minimum_confidence=min_conf),
        thresholds=ScoringThresholds(
            approved=th_app, approved_with_adjustments=th_adj, boundary_review_margin=margin
        ),
        required_pillars=required or ["internal_history", "search_and_media"],
    )


def test_gate_order_1_insufficient_coverage() -> None:
    evaluator = QualityGateEvaluator()
    profile = create_test_profile(min_cov=0.80)

    # Cobertura de apenas 0.70 < 0.80
    gate_eval = evaluator.evaluate(
        viability_score=85.0,
        coverage_score=0.70,
        confidence_score=0.90,
        pillar_scores={},
        profile=profile,
    )

    assert gate_eval.recommendation == AnalysisRecommendation.INSUFFICIENT_EVIDENCE
    assert gate_eval.passed_gates is False
    assert any("Cobertura insuficiente" in r for r in gate_eval.reasons)


def test_gate_order_1_missing_required_pillar() -> None:
    evaluator = QualityGateEvaluator()
    profile = create_test_profile(required=["internal_history"])

    # Cobertura alta, mas pilar obrigatório não está presente
    pillars = {
        "internal_history": PillarScore(
            pillar_id="internal_history",
            raw_score=0.0,
            weight=0.2,
            confidence=0.0,
            is_present=False,
        )
    }

    gate_eval = evaluator.evaluate(
        viability_score=82.0,
        coverage_score=0.80,
        confidence_score=0.90,
        pillar_scores=pillars,
        profile=profile,
    )

    assert gate_eval.recommendation == AnalysisRecommendation.INSUFFICIENT_EVIDENCE
    assert any("Pilar obrigatório ausente: 'internal_history'" in r for r in gate_eval.reasons)


def test_gate_order_2_boundary_review_margin() -> None:
    evaluator = QualityGateEvaluator()
    profile = create_test_profile(th_app=75.0, margin=3.0)

    # Score 76.5 está dentro da margem de 3.0 pontos de 75.0 (|76.5 - 75.0| = 1.5 < 3.0)
    pillars = {
        "internal_history": PillarScore(
            pillar_id="internal_history",
            raw_score=80.0,
            weight=0.2,
            confidence=0.9,
            is_present=True,
        ),
        "search_and_media": PillarScore(
            pillar_id="search_and_media",
            raw_score=75.0,
            weight=0.2,
            confidence=0.9,
            is_present=True,
        ),
    }

    gate_eval = evaluator.evaluate(
        viability_score=76.5,
        coverage_score=1.0,
        confidence_score=0.90,
        pillar_scores=pillars,
        profile=profile,
    )

    assert gate_eval.recommendation == AnalysisRecommendation.REQUIRES_HUMAN_REVIEW
    assert gate_eval.in_boundary_review_margin is True
    assert any("margem de revisão de fronteira" in r for r in gate_eval.reasons)


def test_gate_order_2_contradictory_signals() -> None:
    evaluator = QualityGateEvaluator()
    profile = create_test_profile(
        margin=0.0
    )  # Margem zerada para testar especificamente contradição

    pillars = {
        PillarType.INTERNAL_HISTORY: PillarScore(
            pillar_id=PillarType.INTERNAL_HISTORY,
            raw_score=80.0,
            weight=0.2,
            confidence=0.9,
            is_present=True,
        ),
        PillarType.SEARCH_AND_MEDIA: PillarScore(
            pillar_id=PillarType.SEARCH_AND_MEDIA,
            raw_score=95.0,
            weight=0.2,
            confidence=0.9,
            is_present=True,
        ),
        PillarType.EMPLOYABILITY: PillarScore(
            pillar_id=PillarType.EMPLOYABILITY,
            raw_score=15.0,
            weight=0.15,
            confidence=0.9,
            is_present=True,
        ),
    }

    gate_eval = evaluator.evaluate(
        viability_score=82.0,
        coverage_score=1.0,
        confidence_score=0.90,
        pillar_scores=pillars,
        profile=profile,
    )

    assert gate_eval.recommendation == AnalysisRecommendation.REQUIRES_HUMAN_REVIEW
    assert any("Sinais conflitantes" in r for r in gate_eval.reasons)


def test_gate_order_3_approved() -> None:
    evaluator = QualityGateEvaluator()
    profile = create_test_profile(th_app=75.0, margin=3.0)

    pillars = {
        "internal_history": PillarScore(
            pillar_id="internal_history",
            raw_score=90.0,
            weight=0.2,
            confidence=0.95,
            is_present=True,
        ),
        "search_and_media": PillarScore(
            pillar_id="search_and_media",
            raw_score=88.0,
            weight=0.2,
            confidence=0.95,
            is_present=True,
        ),
    }

    # Score 88.0 bem acima de 75.0 (distância 13 > margin 3.0)
    gate_eval = evaluator.evaluate(
        viability_score=88.0,
        coverage_score=1.0,
        confidence_score=0.95,
        pillar_scores=pillars,
        profile=profile,
    )

    assert gate_eval.recommendation == AnalysisRecommendation.APPROVED
    assert gate_eval.passed_gates is True


def test_gate_order_4_approved_with_adjustments() -> None:
    evaluator = QualityGateEvaluator()
    profile = create_test_profile(th_app=75.0, th_adj=60.0, margin=2.0)

    pillars = {
        "internal_history": PillarScore(
            pillar_id="internal_history",
            raw_score=70.0,
            weight=0.2,
            confidence=0.9,
            is_present=True,
        ),
        "search_and_media": PillarScore(
            pillar_id="search_and_media",
            raw_score=68.0,
            weight=0.2,
            confidence=0.9,
            is_present=True,
        ),
    }

    # Score 68.0 no intervalo [60.0, 75.0] (distância a 75 é 7 > 2, distância a 60 é 8 > 2)
    gate_eval = evaluator.evaluate(
        viability_score=68.0,
        coverage_score=1.0,
        confidence_score=0.90,
        pillar_scores=pillars,
        profile=profile,
    )

    assert gate_eval.recommendation == AnalysisRecommendation.APPROVED_WITH_ADJUSTMENTS
    assert gate_eval.passed_gates is True


def test_gate_order_5_high_risk() -> None:
    evaluator = QualityGateEvaluator()
    profile = create_test_profile(th_app=75.0, th_adj=60.0, margin=3.0)

    pillars = {
        "internal_history": PillarScore(
            pillar_id="internal_history",
            raw_score=30.0,
            weight=0.2,
            confidence=0.9,
            is_present=True,
        ),
        "search_and_media": PillarScore(
            pillar_id="search_and_media",
            raw_score=25.0,
            weight=0.2,
            confidence=0.9,
            is_present=True,
        ),
    }

    # Score 35.0 bem abaixo de 60 (distância 25 > margin 3.0)
    gate_eval = evaluator.evaluate(
        viability_score=35.0,
        coverage_score=1.0,
        confidence_score=0.90,
        pillar_scores=pillars,
        profile=profile,
    )

    assert gate_eval.recommendation == AnalysisRecommendation.HIGH_RISK
    assert gate_eval.passed_gates is True
