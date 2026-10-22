"""Cliente fake determinístico para JEV / TypeSafe AI."""

from __future__ import annotations

from typing import Any

from prometeus.domain.ports.decision_model import (
    DecisionModelPort,
    DecisionPack,
    DecisionResult,
)


class FakeDecisionClient(DecisionModelPort):
    """Implementação em memória para testes unitários, contratuais e CI."""

    def __init__(
        self,
        default_confidence: float = 0.90,
        simulate_unavailable: bool = False,
        simulate_noul: bool = False,
        canned_choices: dict[str, str] | None = None,
        canned_scores: dict[str, float] | None = None,
    ) -> None:
        self.default_confidence = default_confidence
        self.simulate_unavailable = simulate_unavailable
        self.simulate_noul = simulate_noul
        self.canned_choices = canned_choices or {}
        self.canned_scores = canned_scores or {}

    async def execute_choice(
        self,
        pack: DecisionPack,
        context: dict[str, Any],
        evidence_ids: list[str] | None = None,
    ) -> DecisionResult:
        if self.simulate_unavailable:
            raise ConnectionError("TypeSafe JEV service indisponível (Simulação de queda)")

        if self.simulate_noul or context.get("simulate_noul"):
            return DecisionResult.noul(
                pack_id=pack.pack_id,
                reason="Evidência ausente ou insuficiente no contexto",
                evidence_ids=evidence_ids,
            )

        # Escolhe opção pré-configurada ou a primeira opção válida do pack
        selected = self.canned_choices.get(pack.pack_id)
        if not selected:
            selected = pack.options[0] if pack.options else "default_choice"

        # Distribuição uniforme ou mockada
        dist = {opt: (1.0 if opt == selected else 0.0) for opt in pack.options}

        confidence = float(context.get("override_confidence", self.default_confidence))

        return DecisionResult.choice(
            pack_id=pack.pack_id,
            selected=selected,
            confidence=confidence,
            distribution=dist,
            review_threshold=pack.review_threshold,
            evidence_ids=evidence_ids,
            model_version="jev-fake-v1",
        )

    async def execute_score(
        self,
        pack: DecisionPack,
        context: dict[str, Any],
        evidence_ids: list[str] | None = None,
    ) -> DecisionResult:
        if self.simulate_unavailable:
            raise ConnectionError("TypeSafe JEV service indisponível (Simulação de queda)")

        if self.simulate_noul or context.get("simulate_noul"):
            return DecisionResult.noul(
                pack_id=pack.pack_id,
                reason="Dados insuficientes para pontuação na escala",
                evidence_ids=evidence_ids,
            )

        value = self.canned_scores.get(pack.pack_id)
        if value is None:
            # Score mediano default
            value = (pack.min_score + pack.max_score) / 2.0

        confidence = float(context.get("override_confidence", self.default_confidence))

        return DecisionResult.score(
            pack_id=pack.pack_id,
            value=value,
            confidence=confidence,
            review_threshold=pack.review_threshold,
            evidence_ids=evidence_ids,
            model_version="jev-fake-v1",
        )
