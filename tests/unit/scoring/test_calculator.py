import pytest

from prometeus.domain.configuration import ScoringProfileConfig
from prometeus.domain.scoring.calculator import ScoringCalculator


def test_clamp_utility() -> None:
    calc = ScoringCalculator()
    assert calc._clamp(-10.0) == 0.0
    assert calc._clamp(150.0) == 100.0
    assert calc._clamp(75.5) == 75.5


def test_compute_internal_history_monotonicity() -> None:
    calc = ScoringCalculator()
    score_low, _ = calc.compute_internal_history(
        comparable_fit_score=50.0, conversion_rate=0.05, enrollments_count=10
    )
    score_high, _ = calc.compute_internal_history(
        comparable_fit_score=90.0, conversion_rate=0.15, enrollments_count=40
    )
    assert score_high > score_low


def test_compute_search_and_media_bounds() -> None:
    calc = ScoringCalculator()
    score_zero, _ = calc.compute_search_and_media(monthly_volume=0)
    score_huge, _ = calc.compute_search_and_media(
        monthly_volume=100000, growth_trend_pct=80.0, average_interest=100.0
    )

    assert 0.0 <= score_zero <= 100.0
    assert 0.0 <= score_huge <= 100.0
    assert score_huge > score_zero


def test_compute_pricing_competitiveness_curve() -> None:
    calc = ScoringCalculator()
    # Preço igual à mediana de mercado -> pontuação excelente
    score_perfect, _ = calc.compute_pricing(
        proposed_price_brl=1000.0, market_median_price_brl=1000.0
    )
    # Preço 3x maior que a mediana sem justificativa -> penalizado
    score_expensive, _ = calc.compute_pricing(
        proposed_price_brl=3000.0, market_median_price_brl=1000.0
    )

    assert score_perfect >= 95.0
    assert score_expensive < score_perfect


def test_missing_data_coverage_and_partial_score() -> None:
    calc = ScoringCalculator()
    profile = ScoringProfileConfig(
        profile_id="test-v1",
        weights={
            "internal_history": 0.20,
            "paid_competition": 0.20,
            "search_and_media": 0.20,
            "employability": 0.15,
            "syllabus_fit": 0.15,
            "pricing": 0.10,
        },
    )

    # 4 pilares presentes, 2 ausentes (pricing e employability ausentes -> peso total ausente = 0.25)
    inputs = {
        "internal_history": {"comparable_fit_score": 80.0, "is_present": True},
        "paid_competition": {"ad_count": 4, "competition_index": 0.6, "is_present": True},
        "search_and_media": {"monthly_volume": 1000, "is_present": True},
        "syllabus_fit": {"jev_syllabus_score": 90.0, "is_present": True},
        "employability": {"is_present": False, "missing_reason": "Sem vagas encontradas"},
        "pricing": {"is_present": False, "missing_reason": "Preço não informado"},
    }

    v_score, cov_score, conf_score, part_score, pillar_scores = calc.calculate_all(profile, inputs)

    # Cobertura deve ser exatamente 1.0 - 0.25 = 0.75
    assert cov_score == 0.75
    assert pillar_scores["employability"].is_present is False
    assert pillar_scores["pricing"].is_present is False
    assert pillar_scores["internal_history"].is_present is True
    # Partial score deve ser (V / Coverage)
    expected_partial = v_score / cov_score
    assert part_score == pytest.approx(expected_partial, abs=0.02)
