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

    @staticmethod
    def _observed_weighted_score(
        components: list[tuple[float | None, float]],
        *,
        maximum_confidence: float,
    ) -> tuple[float, float]:
        """Agrega somente componentes observados e penaliza a confiança pela ausência.

        Os pesos ausentes não recebem valores substitutos. Eles são removidos do
        denominador do sub-score e reduzem proporcionalmente a confiança do pilar.
        """
        observed = [(value, weight) for value, weight in components if value is not None]
        if not observed:
            return 0.0, 0.0
        observed_weight = sum(weight for _, weight in observed)
        score = sum(float(value) * weight for value, weight in observed) / observed_weight
        confidence = maximum_confidence * observed_weight
        return round(score, 2), round(confidence, 4)

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

        conv_part = (
            self._clamp((conversion_rate / 0.15) * 100.0) if conversion_rate is not None else None
        )
        vol_part = (
            self._clamp((enrollments_count / 50.0) * 100.0)
            if enrollments_count is not None
            else None
        )
        return self._observed_weighted_score(
            [(comp_part, 0.50), (conv_part, 0.30), (vol_part, 0.20)],
            maximum_confidence=0.90,
        )

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
        ad_part = self._clamp((ad_count / 8.0) * 100.0) if ad_count is not None else None

        # Índice de concorrência Google Ads [0.0, 1.0]
        idx_part = self._clamp(competition_index * 100.0) if competition_index is not None else None

        return self._observed_weighted_score(
            [(ad_part, 0.50), (idx_part, 0.50)],
            maximum_confidence=0.88,
        )

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
        if monthly_volume is None:
            vol_part = None
        elif monthly_volume <= 0:
            vol_part = 10.0
        else:
            vol_part = self._clamp(math.log10(max(10, monthly_volume)) * 25.0 - 15.0)

        # Crescimento de tendência (-30% a +70% mapeado para [0, 100])
        growth_part = self._clamp(growth_trend_pct + 30.0) if growth_trend_pct is not None else None

        # Interesse Google Trends (0 a 100)
        interest_part = self._clamp(average_interest) if average_interest is not None else None

        return self._observed_weighted_score(
            [(vol_part, 0.45), (interest_part, 0.30), (growth_part, 0.25)],
            maximum_confidence=0.92,
        )

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
        sal_part = (
            self._clamp(((salary_median_brl - 4000.0) / 10000.0) * 100.0)
            if salary_median_brl is not None
            else None
        )

        return self._observed_weighted_score(
            [(jobs_part, 0.60), (sal_part, 0.40)],
            maximum_confidence=0.85,
        )

    def compute_syllabus_fit(
        self,
        syllabus_fit_score: float | None = None,
        market_pain_points_covered_pct: float | None = None,
        *,
        jev_syllabus_score: float | None = None,
    ) -> tuple[float, float]:
        """Calcula sub-score e confiança do Pilar A (Aderência da Ementa às Demandas)."""
        observed_syllabus_score = (
            syllabus_fit_score if syllabus_fit_score is not None else jev_syllabus_score
        )
        if observed_syllabus_score is None:
            return 0.0, 0.0

        syllabus_part = self._clamp(observed_syllabus_score)
        pain_part = (
            self._clamp(market_pain_points_covered_pct * 100.0)
            if market_pain_points_covered_pct is not None
            else None
        )

        return self._observed_weighted_score(
            [(syllabus_part, 0.75), (pain_part, 0.25)],
            maximum_confidence=0.90,
        )

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
                    syllabus_fit_score=inputs.get("syllabus_fit_score"),
                    market_pain_points_covered_pct=inputs.get("market_pain_points_covered_pct"),
                    jev_syllabus_score=inputs.get("jev_syllabus_score"),
                )
            elif pillar_key == PillarType.PRICING:
                raw, conf = self.compute_pricing(
                    proposed_price_brl=inputs.get("proposed_price_brl"),
                    market_median_price_brl=inputs.get("market_median_price_brl"),
                )
            else:
                if "raw_score" not in inputs or "confidence" not in inputs:
                    pillar_scores[pillar_key] = PillarScore(
                        pillar_id=pillar_key,
                        raw_score=0.0,
                        weight=weight,
                        confidence=0.0,
                        is_present=False,
                        missing_reason="Pilar sem fórmula ou score explícito verificado",
                        features={},
                    )
                    continue
                raw = self._clamp(float(inputs["raw_score"]))
                conf = self._clamp(float(inputs["confidence"]), 0.0, 1.0)

            if conf <= 0.0:
                pillar_scores[pillar_key] = PillarScore(
                    pillar_id=pillar_key,
                    raw_score=0.0,
                    weight=weight,
                    confidence=0.0,
                    is_present=False,
                    missing_reason=inputs.get(
                        "missing_reason", "Nenhuma feature observada para o pilar"
                    ),
                    features={},
                )
                continue

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
