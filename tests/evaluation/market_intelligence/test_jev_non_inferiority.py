"""Testes para o motor de avaliação de não inferioridade do JEV Híbrido (Fase 6)."""

from __future__ import annotations

from prometeus.application.non_inferiority_service import NonInferiorityEvaluator
from prometeus.domain.ports.decision_model import DecisionType
from prometeus.domain.shadow_decisions import (
    DivergenceCategory,
    NonInferiorityEvaluation,
    ShadowComparisonRecord,
    TaskNonInferiorityCriteria,
)


class TestJEVNonInferiority:
    """Suíte de avaliação de não inferioridade do JEV."""

    def test_pack_meets_non_inferiority_approves_for_hybrid(self) -> None:
        """Quando o JEV atinge o limiar acordado de concordância (>= 90%), aprova para modo híbrido."""
        evaluator = NonInferiorityEvaluator()
        criteria = TaskNonInferiorityCriteria(
            pack_id="market-relevance-v1",
            minimum_agreement_rate=0.90,
            maximum_abstention_rate=0.10,
        )

        # 95 concordâncias de 100
        records = [
            ShadowComparisonRecord(
                pack_id="market-relevance-v1",
                decision_type=DecisionType.CHOICE,
                primary_model="gpt-4o-mini",
                shadow_model="jev-2026.1",
                primary_choice="DIRECT",
                shadow_choice="DIRECT",
                is_concordant=True,
                divergence_category=DivergenceCategory.CONCORDANT,
            )
            for _ in range(95)
        ] + [
            ShadowComparisonRecord(
                pack_id="market-relevance-v1",
                decision_type=DecisionType.CHOICE,
                primary_model="gpt-4o-mini",
                shadow_model="jev-2026.1",
                primary_choice="DIRECT",
                shadow_choice="ADJACENT",
                is_concordant=False,
                divergence_category=DivergenceCategory.CHOICE_DIVERGENCE,
            )
            for _ in range(5)
        ]

        evaluation: NonInferiorityEvaluation = evaluator.evaluate_pack(
            pack_id="market-relevance-v1",
            records=records,
            criteria=criteria,
        )

        assert evaluation.total_evaluations == 100
        assert evaluation.agreement_rate == 0.95
        assert evaluation.verdict == "APPROVED_FOR_HYBRID"
        assert "aprovado para rota híbrida" in evaluation.rationale.lower()

    def test_pack_fails_non_inferiority_retains_traditional_route(self) -> None:
        """Quando o JEV não atinge a concordância mínima ou tem alta abstenção, mantém rota tradicional."""
        evaluator = NonInferiorityEvaluator()
        criteria = TaskNonInferiorityCriteria(
            pack_id="evidence-support-v1",
            minimum_agreement_rate=0.95,  # Tarefa crítica de suporte factual
            maximum_abstention_rate=0.05,
            risk_level="HIGH",
        )

        # Apenas 80 concordâncias em 100
        records = [
            ShadowComparisonRecord(
                pack_id="evidence-support-v1",
                decision_type=DecisionType.CHOICE,
                primary_model="gpt-4o-mini",
                shadow_model="jev-2026.1",
                primary_choice="OBSERVED",
                shadow_choice="OBSERVED",
                is_concordant=True,
                divergence_category=DivergenceCategory.CONCORDANT,
            )
            for _ in range(80)
        ] + [
            ShadowComparisonRecord(
                pack_id="evidence-support-v1",
                decision_type=DecisionType.CHOICE,
                primary_model="gpt-4o-mini",
                shadow_model="jev-2026.1",
                primary_choice="OBSERVED",
                shadow_choice="UNSUPPORTED",
                is_concordant=False,
                divergence_category=DivergenceCategory.CHOICE_DIVERGENCE,
            )
            for _ in range(20)
        ]

        evaluation = evaluator.evaluate_pack(
            pack_id="evidence-support-v1",
            records=records,
            criteria=criteria,
        )

        assert evaluation.agreement_rate == 0.80
        assert evaluation.verdict == "RETAIN_TRADITIONAL"
        assert "manter rota tradicional" in evaluation.rationale.lower()
