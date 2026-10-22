"""Serviço de aplicação para compilação, síntese generativa e verificação de dossiês (Fase 06).

Orquestra as etapas 12 (síntese) e 13 (verificação) do workflow do Prometeus.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.domain.dossiers import (
    DossierFactItem,
    DossierFacts,
    DossierOutput,
)
from prometeus.domain.ports.generative_model import GenerativeModelPort
from prometeus.infrastructure.db.models import (
    AnalysisModel,
    DecisionResultModel,
    DossierModel,
    MarketEvidenceModel,
    ScoringResultModel,
)

logger = logging.getLogger(__name__)


class DossierSynthesisService:
    """Orquestrador do ciclo de vida do dossiê: agregação factual -> LLM -> verificação -> persistência."""

    def __init__(
        self,
        db_session: AsyncSession,
        llm_client: GenerativeModelPort,
        verifier: DossierVerifier | None = None,
    ) -> None:
        self.db = db_session
        self.llm = llm_client
        self.verifier = verifier or DossierVerifier()

    async def build_facts(self, analysis_id: str) -> DossierFacts:
        """Carrega e consolida todas as evidências, decisões e scores em um DossierFacts canônico."""
        # 1. Busca Análise
        stmt_analysis = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
        analysis = (await self.db.execute(stmt_analysis)).scalar_one_or_none()
        if not analysis:
            raise ValueError(f"Análise não encontrada para o id: {analysis_id}")

        # 2. Busca Scoring
        stmt_scoring = select(ScoringResultModel).where(
            ScoringResultModel.analysis_id == analysis_id
        )
        scoring = (await self.db.execute(stmt_scoring)).scalar_one_or_none()
        if not scoring:
            raise ValueError(f"A análise {analysis_id} não possui resultado de scoring calculado")

        # 3. Busca Evidências de Mercado
        stmt_evidences = (
            select(MarketEvidenceModel)
            .where(MarketEvidenceModel.analysis_id == analysis_id)
            .order_by(MarketEvidenceModel.collected_at)
        )
        evidences = (await self.db.execute(stmt_evidences)).scalars().all()

        # 4. Busca Decisões do JEV
        stmt_decisions = select(DecisionResultModel).where(
            DecisionResultModel.analysis_id == analysis_id
        )
        decisions = (await self.db.execute(stmt_decisions)).scalars().all()

        fact_items: list[DossierFactItem] = []

        # Adiciona evidências de mercado
        for ev in evidences:
            sanitized = ev.sanitized_data or {}
            metrics: dict[str, Any] = {}
            if "monthly_volume" in sanitized:
                metrics["volume"] = sanitized["monthly_volume"]
            if "cpc_brl" in sanitized:
                metrics["cpc_brl"] = sanitized["cpc_brl"]
            if "competition_index" in sanitized:
                metrics["competition_index"] = sanitized["competition_index"]
            if "open_jobs_count" in sanitized:
                metrics["open_jobs_count"] = sanitized["open_jobs_count"]
            if "salary_median_brl" in sanitized:
                metrics["salary_median_brl"] = sanitized["salary_median_brl"]
            if "market_median_price_brl" in sanitized:
                metrics["market_median_price_brl"] = sanitized["market_median_price_brl"]

            fact_items.append(
                DossierFactItem(
                    evidence_id=ev.id,
                    source_type=ev.evidence_type,
                    title=ev.title,
                    key_metrics=metrics,
                    summary=f"Evidência de mercado tipo {ev.evidence_type}: {ev.title}",
                )
            )

        # Adiciona decisões do JEV
        for dec in decisions:
            fact_items.append(
                DossierFactItem(
                    evidence_id=dec.id,
                    source_type="jev_decision",
                    title=f"Decisão JEV {dec.pack_id}",
                    key_metrics={
                        "confidence": dec.confidence,
                        "score_value": dec.score_value or 0.0,
                    },
                    summary=(
                        f"Julgamento {dec.pack_id} ({dec.decision_type}): "
                        f"escolha={dec.selected_choice}, score={dec.score_value}"
                    ),
                )
            )

        # Extrai sub-scores por pilar
        pillar_summaries: dict[str, float] = {}
        limitations: list[str] = []
        if isinstance(scoring.pillar_scores, dict):
            for p_key, p_data in scoring.pillar_scores.items():
                if isinstance(p_data, dict):
                    raw = float(p_data.get("raw_score", 0.0))
                    pillar_summaries[p_key] = raw
                    if not p_data.get("is_present", True):
                        reason = p_data.get("missing_reason", "Ausência de dados")
                        limitations.append(f"Pilar {p_key} ausente: {reason}")

        target_audience = "Profissionais de mercado e líderes em transição de carreira"
        if analysis.course_name:
            target_audience = (
                f"Especialistas e profissionais interessados em {analysis.course_name}"
            )

        return DossierFacts(
            analysis_id=analysis_id,
            course_name=analysis.course_name,
            target_audience=target_audience,
            recommendation=scoring.recommendation,
            viability_score=scoring.viability_score,
            coverage_score=scoring.coverage_score,
            confidence_score=scoring.confidence_score,
            pillar_summaries=pillar_summaries,
            items=fact_items,
            limitations=limitations,
        )

    async def synthesize_and_verify(
        self,
        analysis_id: str,
        prompt_version: str = "dossier-v1",
    ) -> DossierOutput:
        """Gera o dossiê com a LLM, valida rigorosamente as claims e persiste em PostgreSQL."""
        facts = await self.build_facts(analysis_id)

        # Geração pela LLM generativa
        raw_dossier = await self.llm.synthesize_dossier(facts, prompt_version=prompt_version)

        # Verificação determinística (TOOL-15)
        verified_dossier = self.verifier.verify(raw_dossier, facts)

        # Persistência relacional em PostgreSQL
        stmt_exist = select(DossierModel).where(DossierModel.analysis_id == analysis_id)
        existing = (await self.db.execute(stmt_exist)).scalar_one_or_none()

        sections_payload = [s.model_dump() for s in verified_dossier.sections]
        claims_payload = [c.model_dump() for c in verified_dossier.claims]

        if existing:
            existing.prompt_version = verified_dossier.prompt_version
            existing.model_name = verified_dossier.model_name
            existing.facts_hash = verified_dossier.facts_hash
            existing.status = verified_dossier.status.value
            existing.executive_summary = verified_dossier.executive_summary
            existing.sections = sections_payload
            existing.claims = claims_payload
            existing.cost_usd = verified_dossier.cost_usd
        else:
            model = DossierModel(
                id=verified_dossier.id,
                analysis_id=analysis_id,
                prompt_version=verified_dossier.prompt_version,
                model_name=verified_dossier.model_name,
                facts_hash=verified_dossier.facts_hash,
                status=verified_dossier.status.value,
                executive_summary=verified_dossier.executive_summary,
                sections=sections_payload,
                claims=claims_payload,
                cost_usd=verified_dossier.cost_usd,
            )
            self.db.add(model)

        await self.db.commit()
        return verified_dossier
