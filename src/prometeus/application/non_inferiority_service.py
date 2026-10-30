"""Serviço de avaliação de não inferioridade para homologação de decisão híbrida JEV (Fase 6)."""

from __future__ import annotations

from collections import Counter
from typing import Literal

from prometeus.domain.shadow_decisions import (
    NonInferiorityEvaluation,
    ShadowComparisonRecord,
    TaskNonInferiorityCriteria,
)


class NonInferiorityEvaluator:
    """Avalia se um modelo JEV atinge os critérios pré-acordados de não inferioridade contra a LLM tradicional."""

    def evaluate_pack(
        self,
        pack_id: str,
        records: list[ShadowComparisonRecord],
        criteria: TaskNonInferiorityCriteria | None = None,
    ) -> NonInferiorityEvaluation:
        criteria = criteria or TaskNonInferiorityCriteria(pack_id=pack_id)
        pack_records = [r for r in records if r.pack_id == pack_id]

        total = len(pack_records)
        if total == 0:
            return NonInferiorityEvaluation(
                pack_id=pack_id,
                total_evaluations=0,
                concordant_count=0,
                agreement_rate=0.0,
                shadow_abstention_rate=0.0,
                primary_abstention_rate=0.0,
                latency_delta_mean_ms=0.0,
                divergence_counts={},
                criteria=criteria,
                verdict="RETAIN_TRADITIONAL",
                rationale="Nenhum registro de comparação disponível para avaliação.",
            )

        concordant_count = sum(1 for r in pack_records if r.is_concordant)
        agreement_rate = concordant_count / total
        shadow_abstentions = sum(1 for r in pack_records if r.shadow_is_noul)
        primary_abstentions = sum(1 for r in pack_records if r.primary_is_noul)
        shadow_abstention_rate = shadow_abstentions / total
        primary_abstention_rate = primary_abstentions / total

        latency_deltas = [r.shadow_latency_ms - r.primary_latency_ms for r in pack_records]
        latency_delta_mean_ms = sum(latency_deltas) / len(latency_deltas)

        div_counts = dict(Counter(r.divergence_category.value for r in pack_records))

        passed_agreement = agreement_rate >= criteria.minimum_agreement_rate
        passed_abstention = shadow_abstention_rate <= criteria.maximum_abstention_rate

        shadow_model = pack_records[0].shadow_model if pack_records else "JEV"

        verdict: Literal["APPROVED_FOR_HYBRID", "RETAIN_TRADITIONAL"]
        if passed_agreement and passed_abstention:
            verdict = "APPROVED_FOR_HYBRID"
            rationale = (
                f"O modelo shadow {shadow_model} atingiu os critérios de não inferioridade para o pack '{pack_id}' "
                f"com taxa de concordância de {agreement_rate * 100:.1f}% (mínimo: {criteria.minimum_agreement_rate * 100:.1f}%) "
                f"e taxa de abstenção de {shadow_abstention_rate * 100:.1f}% (máximo: {criteria.maximum_abstention_rate * 100:.1f}%). "
                f"Aprovado para rota híbrida."
            )
        else:
            verdict = "RETAIN_TRADITIONAL"
            reasons = []
            if not passed_agreement:
                reasons.append(
                    f"concordância {agreement_rate * 100:.1f}% abaixo do limiar de {criteria.minimum_agreement_rate * 100:.1f}%"
                )
            if not passed_abstention:
                reasons.append(
                    f"abstenção {shadow_abstention_rate * 100:.1f}% acima do tolerado de {criteria.maximum_abstention_rate * 100:.1f}%"
                )
            rationale = (
                f"O modelo shadow {shadow_model} não atingiu os critérios para o pack '{pack_id}': "
                f"{', '.join(reasons)}. Decisão acordada: manter rota tradicional para este pack."
            )

        return NonInferiorityEvaluation(
            pack_id=pack_id,
            total_evaluations=total,
            concordant_count=concordant_count,
            agreement_rate=round(agreement_rate, 4),
            shadow_abstention_rate=round(shadow_abstention_rate, 4),
            primary_abstention_rate=round(primary_abstention_rate, 4),
            latency_delta_mean_ms=round(latency_delta_mean_ms, 2),
            divergence_counts=div_counts,
            criteria=criteria,
            verdict=verdict,
            rationale=rationale,
        )
