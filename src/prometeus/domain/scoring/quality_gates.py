"""Avaliador determinístico de Quality Gates e definição da recomendação (Etapa 11).

Segue estritamente a ordem de avaliação e limiares do baseline (docs/scoring/scoring-model.md)
e do ADR-0005. LLM e JEV jamais definem este campo.
"""

from __future__ import annotations

from prometeus.domain.analyses import AnalysisRecommendation
from prometeus.domain.configuration import ScoringProfileConfig
from prometeus.domain.scoring.models import (
    GateEvaluation,
    PillarScore,
    PillarType,
)


class QualityGateEvaluator:
    """Avalia gates de cobertura, confiança, limites de fronteira e contradições."""

    def evaluate(
        self,
        viability_score: float,
        coverage_score: float,
        confidence_score: float,
        pillar_scores: dict[str, PillarScore],
        profile: ScoringProfileConfig,
        pending_review_pillars: list[str] | None = None,
    ) -> GateEvaluation:
        """Executa a ordem de avaliação da recomendação (a primeira verdadeira vence)."""
        reasons: list[str] = []
        if pending_review_pillars:
            reasons.append(
                "Julgamentos pendentes de revisão humana: " + ", ".join(pending_review_pillars)
            )

        # Cálculo de distâncias aos limiares de decisão
        th_app = profile.thresholds.approved
        th_adj = profile.thresholds.approved_with_adjustments
        margin = profile.thresholds.boundary_review_margin

        dist_app = round(abs(viability_score - th_app), 2)
        dist_adj = round(abs(viability_score - th_adj), 2)
        in_margin = (dist_app < margin) or (dist_adj < margin)

        # -----------------------------------------------------------------
        # Ordem 1: INSUFFICIENT_EVIDENCE
        # -----------------------------------------------------------------
        insufficient = False

        if coverage_score < profile.gates.minimum_coverage:
            insufficient = True
            reasons.append(
                f"Cobertura insuficiente: {coverage_score:.1%} < {profile.gates.minimum_coverage:.1%}"
            )

        if confidence_score < profile.gates.minimum_confidence:
            insufficient = True
            reasons.append(
                f"Confiança média insuficiente: {confidence_score:.1%} < {profile.gates.minimum_confidence:.1%}"
            )

        for req in profile.required_pillars:
            p = pillar_scores.get(req)
            if not p or not p.is_present:
                insufficient = True
                reasons.append(f"Pilar obrigatório ausente: '{req}'")

        if insufficient:
            return GateEvaluation(
                recommendation=AnalysisRecommendation.INSUFFICIENT_EVIDENCE,
                passed_gates=False,
                viability_score=viability_score,
                coverage_score=coverage_score,
                confidence_score=confidence_score,
                reasons=reasons,
                distance_to_approved_threshold=dist_app,
                distance_to_adjustment_threshold=dist_adj,
                in_boundary_review_margin=in_margin,
            )

        # -----------------------------------------------------------------
        # Ordem 2: REQUIRES_HUMAN_REVIEW
        # -----------------------------------------------------------------
        if pending_review_pillars:
            return GateEvaluation(
                recommendation=AnalysisRecommendation.REQUIRES_HUMAN_REVIEW,
                passed_gates=False,
                viability_score=viability_score,
                coverage_score=coverage_score,
                confidence_score=confidence_score,
                reasons=reasons,
                distance_to_approved_threshold=dist_app,
                distance_to_adjustment_threshold=dist_adj,
                in_boundary_review_margin=in_margin,
            )
        # Caso A: Fronteira de decisão (zona de incerteza dentro da margem)
        if in_margin:
            reasons.append(
                f"Score V={viability_score:.2f} está na margem de revisão de fronteira (+/-{margin:.1f} pontos dos limiares {th_app} ou {th_adj})"
            )
            return GateEvaluation(
                recommendation=AnalysisRecommendation.REQUIRES_HUMAN_REVIEW,
                passed_gates=False,
                viability_score=viability_score,
                coverage_score=coverage_score,
                confidence_score=confidence_score,
                reasons=reasons,
                distance_to_approved_threshold=dist_app,
                distance_to_adjustment_threshold=dist_adj,
                in_boundary_review_margin=True,
            )

        # Caso B: Sinais conflitantes severos entre pilares principais
        search_p = pillar_scores.get(PillarType.SEARCH_AND_MEDIA)
        job_p = pillar_scores.get(PillarType.EMPLOYABILITY)
        if search_p and job_p and search_p.is_present and job_p.is_present:
            if search_p.raw_score >= 85.0 and job_p.raw_score <= 25.0:
                reasons.append(
                    f"Sinais conflitantes: Alta busca ({search_p.raw_score:.1f}) com baixa empregabilidade ({job_p.raw_score:.1f})"
                )
                return GateEvaluation(
                    recommendation=AnalysisRecommendation.REQUIRES_HUMAN_REVIEW,
                    passed_gates=False,
                    viability_score=viability_score,
                    coverage_score=coverage_score,
                    confidence_score=confidence_score,
                    reasons=reasons,
                    distance_to_approved_threshold=dist_app,
                    distance_to_adjustment_threshold=dist_adj,
                    in_boundary_review_margin=False,
                )

        # -----------------------------------------------------------------
        # Ordem 3: APPROVED
        # -----------------------------------------------------------------
        if viability_score >= th_app:
            reasons.append(
                f"Score V={viability_score:.2f} atinge critério de aprovação (>= {th_app})"
            )
            return GateEvaluation(
                recommendation=AnalysisRecommendation.APPROVED,
                passed_gates=True,
                viability_score=viability_score,
                coverage_score=coverage_score,
                confidence_score=confidence_score,
                reasons=reasons,
                distance_to_approved_threshold=dist_app,
                distance_to_adjustment_threshold=dist_adj,
                in_boundary_review_margin=False,
            )

        # -----------------------------------------------------------------
        # Ordem 4: APPROVED_WITH_ADJUSTMENTS
        # -----------------------------------------------------------------
        if viability_score >= th_adj:
            reasons.append(
                f"Score V={viability_score:.2f} na faixa de aprovação com ajustes ({th_adj} a {th_app})"
            )
            return GateEvaluation(
                recommendation=AnalysisRecommendation.APPROVED_WITH_ADJUSTMENTS,
                passed_gates=True,
                viability_score=viability_score,
                coverage_score=coverage_score,
                confidence_score=confidence_score,
                reasons=reasons,
                distance_to_approved_threshold=dist_app,
                distance_to_adjustment_threshold=dist_adj,
                in_boundary_review_margin=False,
            )

        # -----------------------------------------------------------------
        # Ordem 5: HIGH_RISK
        # -----------------------------------------------------------------
        reasons.append(f"Score V={viability_score:.2f} abaixo do limiar mínimo (< {th_adj})")
        return GateEvaluation(
            recommendation=AnalysisRecommendation.HIGH_RISK,
            passed_gates=True,
            viability_score=viability_score,
            coverage_score=coverage_score,
            confidence_score=confidence_score,
            reasons=reasons,
            distance_to_approved_threshold=dist_app,
            distance_to_adjustment_threshold=dist_adj,
            in_boundary_review_margin=False,
        )
