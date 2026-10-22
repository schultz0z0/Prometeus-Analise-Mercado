"""Cálculo determinístico de sub-scores, cobertura e índices de viabilidade (Etapa 10).

Implementa monotonicidade estrita, limites bounded em [0, 100] e ausência de dependência de IA
para cálculos matemáticos e financeiros (ADR-0003, ADR-0005 e AGENTS.md).
"""

from __future__ import annotations

import math
from typing import Any

from prometeus.domain.configuration import ScoringProfileConfig
from prometeus.domain.scoring.models import (
    PillarScore,
    PillarType,
)


class ScoringCalculator:
    """Motor determinístico para cálculo de sub-scores por pilar e índices agregados."""

    @staticmethod
    def _clamp(val: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
        """Limita valor estritamente ao intervalo [min_val, max_val]."""
        return max(min_val, min(max_val, val))

    def compute_internal_history(
        self,
        comparable_fit_score: float | None,
        conversion_rate: float | None = None,
        enrollments_count: int | None = None,
    ) -> tuple[float, float]:
        """Calcula sub-score e confiança do Pilar H (Histórico Interno)."""
        if comparable_fit_score is None:
            return 0.0, 0.0

        comp_part = self._clamp(comparable_fit_score)

        # Conversão de 0% a 20% mapeada para [0, 100]
        if conversion_rate is not None:
            conv_part = self._clamp((conversion_rate / 0.15) * 100.0)
        else:
            conv_part = comp_part

        # Volume de matrículas históricas (0 a 100 alunos)
        if enrollments_count is not None:
            vol_part = self._clamp((enrollments_count / 50.0) * 100.0)
        else:
            vol_part = comp_part

        raw_score = 0.50 * comp_part + 0.30 * conv_part + 0.20 * vol_part
        confidence = (
            0.90 if (conversion_rate is not None and enrollments_count is not None) else 0.70
        )
        return round(raw_score, 2), confidence

    def compute_paid_competition(
        self,
        ad_count: int | None,
        competition_index: float | None,
        cpc_brl: float | None = None,
    ) -> tuple[float, float]:
        """Calcula sub-score e confiança do Pilar C (Concorrência Paga)."""
        if ad_count is None and competition_index is None:
            return 0.0, 0.0

        # Anúncios concorrentes (proxy de validação de mercado e apetite de compra)
        ad_val = ad_count or 0
        ad_part = self._clamp((ad_val / 8.0) * 100.0)

        # Índice de concorrência Google Ads [0.0, 1.0]
        comp_idx = competition_index if competition_index is not None else 0.5
        idx_part = self._clamp(comp_idx * 100.0)

        raw_score = 0.50 * ad_part + 0.50 * idx_part
        confidence = 0.88 if (ad_count is not None and competition_index is not None) else 0.65
        return round(raw_score, 2), confidence

    def compute_search_and_media(
        self,
        monthly_volume: int | None,
        growth_trend_pct: float | None = None,
        average_interest: float | None = None,
    ) -> tuple[float, float]:
        """Calcula sub-score e confiança do Pilar B (Busca e Viabilidade de Mídia)."""
        if monthly_volume is None and average_interest is None:
            return 0.0, 0.0

        # Volume de busca mensal em escala logarítmica suave
        vol = monthly_volume or 0
        if vol <= 0:
            vol_part = 10.0
        else:
            # log10(100) = 2 -> 30; log10(1000) = 3 -> 60; log10(10000) = 4 -> 90
            vol_part = self._clamp(math.log10(max(10, vol)) * 25.0 - 15.0)

        # Crescimento de tendência (-30% a +70% mapeado para [0, 100])
        growth = growth_trend_pct if growth_trend_pct is not None else 10.0
        growth_part = self._clamp(((growth + 30.0) / 100.0) * 100.0)

        # Interesse Google Trends (0 a 100)
        interest_part = self._clamp(average_interest if average_interest is not None else 60.0)

        raw_score = 0.45 * vol_part + 0.30 * interest_part + 0.25 * growth_part
        confidence = 0.92 if (monthly_volume is not None and average_interest is not None) else 0.70
        return round(raw_score, 2), confidence

    def compute_employability(
        self,
        open_jobs_count: int | None,
        salary_median_brl: float | None = None,
    ) -> tuple[float, float]:
        """Calcula sub-score e confiança do Pilar E (Empregabilidade e Vagas)."""
        if open_jobs_count is None:
            return 0.0, 0.0

        # Volume de vagas ativas (0 a 50 vagas mapeado para [0, 100])
        jobs_part = self._clamp((open_jobs_count / 30.0) * 100.0)

        # Salário mediano de mercado (R$ 4.000 a R$ 14.000)
        if salary_median_brl is not None:
            sal_part = self._clamp(((salary_median_brl - 4000.0) / 10000.0) * 100.0)
        else:
            sal_part = jobs_part

        raw_score = 0.60 * jobs_part + 0.40 * sal_part
        confidence = 0.85 if salary_median_brl is not None else 0.72
        return round(raw_score, 2), confidence

    def compute_syllabus_fit(
        self,
        jev_syllabus_score: float | None,
        market_pain_points_covered_pct: float | None = None,
    ) -> tuple[float, float]:
        """Calcula sub-score e confiança do Pilar A (Aderência da Ementa às Demandas)."""
        if jev_syllabus_score is None:
            return 0.0, 0.0

        jev_part = self._clamp(jev_syllabus_score)
        pain_part = self._clamp((market_pain_points_covered_pct or 0.80) * 100.0)

        raw_score = 0.75 * jev_part + 0.25 * pain_part
        confidence = 0.90
        return round(raw_score, 2), confidence

    def compute_pricing(
        self,
        proposed_price_brl: float | None,
        market_median_price_brl: float | None,
    ) -> tuple[float, float]:
        """Calcula sub-score e confiança do Pilar P (Precificação e Competitividade)."""
        if (
            proposed_price_brl is None
            or market_median_price_brl is None
            or market_median_price_brl <= 0
        ):
            return 0.0, 0.0

        # Relação de preço: proposto / mediana do mercado
        ratio = proposed_price_brl / market_median_price_brl

        # Curva de competitividade:
        # Se ratio ~= 1.0 (preço exatamente na mediana) -> 95
        # Se 0.8 <= ratio <= 1.2 -> 90 a 100
        # Se muito barato (< 0.4) desconfiança -> penaliza levemente (60)
        # Se muito caro (> 2.0) -> penaliza forte (30)
        if 0.7 <= ratio <= 1.3:
            raw_score = 100.0 - abs(ratio - 1.0) * 50.0
        elif ratio < 0.7:
            raw_score = self._clamp(50.0 + (ratio / 0.7) * 40.0)
        else:
            raw_score = self._clamp(90.0 - (ratio - 1.3) * 60.0)

        confidence = 0.85
        return round(raw_score, 2), confidence

    def calculate_all(
        self,
        profile: ScoringProfileConfig,
        pillar_inputs: dict[str, dict[str, Any]],
    ) -> tuple[float, float, float, float, dict[str, PillarScore]]:
        """Calcula todos os sub-scores e índices agregados (V, Coverage, Confidence, Partial)."""
        pillar_scores: dict[str, PillarScore] = {}

        for pillar_key, weight in profile.weights.items():
            inputs = pillar_inputs.get(pillar_key, {})
            is_present = inputs.get("is_present", True) if inputs else False

            if not is_present or not inputs:
                pillar_scores[pillar_key] = PillarScore(
                    pillar_id=pillar_key,
                    raw_score=0.0,
                    weight=weight,
                    confidence=0.0,
                    is_present=False,
                    missing_reason=inputs.get("missing_reason", "Dados ausentes para o pilar"),
                    features={},
                )
                continue

            # Despacho determinístico por pilar
            if pillar_key == PillarType.INTERNAL_HISTORY:
                raw, conf = self.compute_internal_history(
                    comparable_fit_score=inputs.get("comparable_fit_score"),
                    conversion_rate=inputs.get("conversion_rate"),
                    enrollments_count=inputs.get("enrollments_count"),
                )
            elif pillar_key == PillarType.PAID_COMPETITION:
                raw, conf = self.compute_paid_competition(
                    ad_count=inputs.get("ad_count"),
                    competition_index=inputs.get("competition_index"),
                    cpc_brl=inputs.get("cpc_brl"),
                )
            elif pillar_key == PillarType.SEARCH_AND_MEDIA:
                raw, conf = self.compute_search_and_media(
                    monthly_volume=inputs.get("monthly_volume"),
                    growth_trend_pct=inputs.get("growth_trend_pct"),
                    average_interest=inputs.get("average_interest"),
                )
            elif pillar_key == PillarType.EMPLOYABILITY:
                raw, conf = self.compute_employability(
                    open_jobs_count=inputs.get("open_jobs_count"),
                    salary_median_brl=inputs.get("salary_median_brl"),
                )
            elif pillar_key == PillarType.SYLLABUS_FIT:
                raw, conf = self.compute_syllabus_fit(
                    jev_syllabus_score=inputs.get("jev_syllabus_score"),
                    market_pain_points_covered_pct=inputs.get("market_pain_points_covered_pct"),
                )
            elif pillar_key == PillarType.PRICING:
                raw, conf = self.compute_pricing(
                    proposed_price_brl=inputs.get("proposed_price_brl"),
                    market_median_price_brl=inputs.get("market_median_price_brl"),
                )
            else:
                raw = self._clamp(float(inputs.get("raw_score", 50.0)))
                conf = float(inputs.get("confidence", 0.70))

            pillar_scores[pillar_key] = PillarScore(
                pillar_id=pillar_key,
                raw_score=raw,
                weight=weight,
                confidence=conf,
                is_present=True,
                missing_reason=None,
                features=inputs,
            )

        # Índices agregados canônicos
        present_pillars = [p for p in pillar_scores.values() if p.is_present]
        coverage_score = round(sum(p.weight for p in present_pillars), 4)

        if coverage_score > 0.0:
            weighted_sum = sum(p.weighted_score for p in present_pillars)
            partial_score = round(weighted_sum / coverage_score, 2)
            confidence_score = round(
                sum(p.weighted_confidence for p in present_pillars) / coverage_score, 4
            )
            # Viability score V: soma das contribuições ponderadas reais
            viability_score = round(weighted_sum, 2)
        else:
            partial_score = 0.0
            confidence_score = 0.0
            viability_score = 0.0

        return viability_score, coverage_score, confidence_score, partial_score, pillar_scores
