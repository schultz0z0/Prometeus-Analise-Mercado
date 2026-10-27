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
    ResearchPlanModel,
    ScoringResultModel,
)

logger = logging.getLogger(__name__)


class DossierVerificationError(RuntimeError):
    """O conteúdo gerado não pode ser publicado porque falhou no gate factual."""


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

        stmt_plan = (
            select(ResearchPlanModel)
            .where(ResearchPlanModel.analysis_id == analysis_id)
            .order_by(ResearchPlanModel.created_at.desc())
        )
        research_plan = (await self.db.execute(stmt_plan)).scalars().first()

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

            summary_parts = [f"Evidência de mercado tipo {ev.evidence_type}: {ev.title}"]
            organic = sanitized.get("organicResults")
            if isinstance(organic, list) and organic:
                snippets: list[str] = []
                for entry in organic[:4]:
                    if isinstance(entry, dict):
                        t = str(entry.get("title") or "").strip()
                        d = str(entry.get("description") or "").strip()
                        if t or d:
                            snippets.append(f"{t} ({d[:140]})" if d else t)
                if snippets:
                    summary_parts.append("Resultados: " + " | ".join(snippets))
            else:
                for text_key in ("description", "text", "markdown", "caption", "comment", "body"):
                    val = sanitized.get(text_key)
                    if isinstance(val, str) and val.strip():
                        summary_parts.append(val.strip()[:300])
                        break
                extra_meta = [
                    f"{k}={sanitized[k]}"
                    for k in ("companyName", "company", "positionName", "location", "pageName")
                    if isinstance(sanitized.get(k), str) and str(sanitized.get(k)).strip()
                ]
                if extra_meta:
                    summary_parts.append(", ".join(extra_meta))

            fact_items.append(
                DossierFactItem(
                    evidence_id=ev.id,
                    source_type=ev.evidence_type,
                    title=ev.title,
                    key_metrics=metrics,
                    summary=" — ".join(summary_parts)[:600],
                    source_url=ev.source_url,
                )
            )

        # Adiciona julgamentos semânticos do modo ativo (LLM tradicional ou híbrido)
        for dec in decisions:
            decision_metrics: dict[str, Any] = {"confidence": dec.confidence}
            if dec.score_value is not None:
                decision_metrics["score_value"] = dec.score_value
            fact_items.append(
                DossierFactItem(
                    evidence_id=dec.id,
                    source_type="semantic_decision",
                    title=f"Julgamento semântico {dec.pack_id}",
                    key_metrics=decision_metrics,
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

        understanding_snapshot = (
            dict(research_plan.understanding_snapshot) if research_plan is not None else {}
        )
        plan_snapshot = dict(research_plan.plan_snapshot) if research_plan is not None else {}
        target_audiences = understanding_snapshot.get("target_audiences", [])
        if isinstance(target_audiences, list) and target_audiences:
            target_audience = ", ".join(str(item) for item in target_audiences)
        else:
            target_audience = "Não informado no entendimento do curso"
            limitations.append("Público-alvo não informado no entendimento persistido do curso")

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
            course_understanding=understanding_snapshot,
            research_plan=plan_snapshot,
            counterevidence=[],
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
        if verified_dossier.status.value != "VERIFIED":
            raise DossierVerificationError(
                f"Dossiê da análise {analysis_id} não passou no gate de verificação factual"
            )

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
