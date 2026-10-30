"""Serviço de aplicação para orquestração de julgamentos em Shadow Mode (Fase 6)."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from typing import Any

from prometeus.application.decision_service import DecisionService
from prometeus.domain.analyses import Analysis
from prometeus.domain.ports.decision_model import (
    DecisionModelPort,
    DecisionResult,
    DecisionType,
)
from prometeus.domain.shadow_decisions import (
    DivergenceCategory,
    ShadowComparisonRecord,
)

logger = logging.getLogger(__name__)


class ShadowDecisionService:
    """Orquestrador de execução em shadow mode (ADR-0008, Fase 6).

    Executa a decisão atômica com o modelo primário (cujo resultado rege a produção e scoring)
    e executa em paralelo/shadow com o modelo JEV sobre o EXATO mesmo contexto e evidências,
    registrando latência, divergência, custo e concordância sem jamais quebrar ou alterar a produção.
    """

    def __init__(
        self,
        primary_service: DecisionService,
        shadow_model: DecisionModelPort,
        *,
        enabled: bool = True,
        confidence_delta_tolerance: float = 0.20,
        score_delta_tolerance: float = 5.0,
    ) -> None:
        self.primary_service = primary_service
        self.shadow_model = shadow_model
        self.enabled = enabled
        self.confidence_delta_tolerance = confidence_delta_tolerance
        self.score_delta_tolerance = score_delta_tolerance
        self.comparison_records: list[ShadowComparisonRecord] = []

    async def execute_judgment(
        self,
        pack_id: str,
        context: dict[str, Any],
        analysis: Analysis | None = None,
        correlation_id: str = "none",
        evidence_ids: list[str] | None = None,
        component_versions: Mapping[str, str] | None = None,
        stage: str | None = None,
    ) -> DecisionResult:
        """Executa a decisão primária (produção) e, se habilitado, roda o modelo shadow em sandbox."""
        start_primary = time.perf_counter()
        primary_result = await self.primary_service.execute_judgment(
            pack_id=pack_id,
            context=context,
            analysis=analysis,
            correlation_id=correlation_id,
            evidence_ids=evidence_ids,
            component_versions=component_versions,
            stage=stage,
        )
        primary_latency_ms = (time.perf_counter() - start_primary) * 1000.0

        if self.enabled:
            await self._run_shadow_safe(
                pack_id=pack_id,
                context=context,
                primary_result=primary_result,
                primary_latency_ms=primary_latency_ms,
                evidence_ids=evidence_ids,
            )

        return primary_result

    async def _run_shadow_safe(
        self,
        pack_id: str,
        context: dict[str, Any],
        primary_result: DecisionResult,
        primary_latency_ms: float,
        evidence_ids: list[str] | None = None,
    ) -> None:
        """Executa o modelo shadow isoladamente, garantindo que qualquer falha seja capturada."""
        pack = self.primary_service.get_pack(pack_id)
        primary_id = self.primary_service.decision_model.model_identity()
        shadow_id = self.shadow_model.model_identity()

        start_shadow = time.perf_counter()
        shadow_result: DecisionResult | None = None
        error_msg: str | None = None

        try:
            if pack.decision_type == DecisionType.CHOICE:
                shadow_result = await self.shadow_model.execute_choice(
                    pack=pack,
                    context=context,
                    evidence_ids=evidence_ids,
                )
            elif pack.decision_type == DecisionType.SCORE:
                shadow_result = await self.shadow_model.execute_score(
                    pack=pack,
                    context=context,
                    evidence_ids=evidence_ids,
                )
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.warning(
                f"[Shadow Mode] Falha na execução shadow do pack '{pack_id}' "
                f"com modelo {shadow_id.model}: {exc}"
            )

        shadow_latency_ms = (time.perf_counter() - start_shadow) * 1000.0

        # Classificação de divergência
        if error_msg is not None or shadow_result is None:
            record = ShadowComparisonRecord(
                pack_id=pack_id,
                decision_type=pack.decision_type,
                primary_model=primary_id.model,
                shadow_model=shadow_id.model,
                primary_choice=primary_result.selected_choice,
                primary_score=primary_result.score_value,
                primary_confidence=primary_result.confidence,
                primary_is_noul=primary_result.is_noul,
                is_concordant=False,
                divergence_category=DivergenceCategory.SHADOW_ERROR,
                divergence_notes=error_msg,
                primary_latency_ms=round(primary_latency_ms, 2),
                shadow_latency_ms=round(shadow_latency_ms, 2),
                evidence_ids=list(evidence_ids or []),
            )
            self.comparison_records.append(record)
            return

        is_concordant = True
        divergence = DivergenceCategory.CONCORDANT
        notes: str | None = None

        if primary_result.is_noul != shadow_result.is_noul:
            is_concordant = False
            divergence = DivergenceCategory.ABSTENTION_DIVERGENCE
            notes = (
                f"Divergência de abstenção: primário_noul={primary_result.is_noul}, "
                f"shadow_noul={shadow_result.is_noul}"
            )
        elif primary_result.is_noul and shadow_result.is_noul:
            is_concordant = True
            divergence = DivergenceCategory.CONCORDANT
        elif pack.decision_type == DecisionType.CHOICE:
            if primary_result.selected_choice != shadow_result.selected_choice:
                is_concordant = False
                divergence = DivergenceCategory.CHOICE_DIVERGENCE
                notes = (
                    f"Escolhas diferentes: primário='{primary_result.selected_choice}', "
                    f"shadow='{shadow_result.selected_choice}'"
                )
            elif (
                abs(primary_result.confidence - shadow_result.confidence)
                > self.confidence_delta_tolerance
            ):
                is_concordant = True
                divergence = DivergenceCategory.CONFIDENCE_DIVERGENCE
                notes = (
                    f"Confianças discrepantes: primário={primary_result.confidence:.2f}, "
                    f"shadow={shadow_result.confidence:.2f}"
                )
        elif pack.decision_type == DecisionType.SCORE:
            score_diff = abs(
                (primary_result.score_value or 0.0) - (shadow_result.score_value or 0.0)
            )
            if score_diff > self.score_delta_tolerance:
                is_concordant = False
                divergence = DivergenceCategory.SCORE_DIVERGENCE
                notes = (
                    f"Scores discrepantes: primário={primary_result.score_value}, "
                    f"shadow={shadow_result.score_value} (delta={score_diff:.2f})"
                )
            elif (
                abs(primary_result.confidence - shadow_result.confidence)
                > self.confidence_delta_tolerance
            ):
                is_concordant = True
                divergence = DivergenceCategory.CONFIDENCE_DIVERGENCE
                notes = (
                    f"Confianças discrepantes: primário={primary_result.confidence:.2f}, "
                    f"shadow={shadow_result.confidence:.2f}"
                )

        record = ShadowComparisonRecord(
            pack_id=pack_id,
            decision_type=pack.decision_type,
            primary_model=primary_id.model,
            shadow_model=shadow_id.model,
            primary_choice=primary_result.selected_choice,
            shadow_choice=shadow_result.selected_choice,
            primary_score=primary_result.score_value,
            shadow_score=shadow_result.score_value,
            primary_confidence=primary_result.confidence,
            shadow_confidence=shadow_result.confidence,
            primary_is_noul=primary_result.is_noul,
            shadow_is_noul=shadow_result.is_noul,
            is_concordant=is_concordant,
            divergence_category=divergence,
            divergence_notes=notes,
            primary_latency_ms=round(primary_latency_ms, 2),
            shadow_latency_ms=round(shadow_latency_ms, 2),
            evidence_ids=list(evidence_ids or []),
        )
        self.comparison_records.append(record)

