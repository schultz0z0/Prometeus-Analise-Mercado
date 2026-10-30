"""Diagnóstico causal de lacunas de pesquisa e ganho marginal (Tarefa 2.4).

Classifica cada lacuna nas 7 causas canônicas antes de qualquer nova chamada:
1. source_failure: falha técnica/provedor (ação: retry com backoff)
2. unsupported_source: capacidade não suportada pelo conector (ação: limitação declarada)
3. normalization_loss: dado recebido mas perdido no parser (ação: reprocessar dado existente sem custo)
4. context_projection_loss: dado normalizado mas cortado na projeção (ação: reprojetar contexto sem custo)
5. qualification_uncertain: evidência observada com qualificação inconclusiva (ação: refinar rubrica)
6. true_no_signal: busca correta executada com ausência genuína no mercado (ação: aceitar zero)
7. missing_primary_data: dados internos ou primários não públicos (ação: pedir dados ENS)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from prometeus.application.evidence_features import EvidenceFeatureSet


class GapCause(StrEnum):
    """Causas canônicas de ausência de evidência sem equivalência arbitrária."""

    SOURCE_FAILURE = "source_failure"
    UNSUPPORTED_SOURCE = "unsupported_source"
    NORMALIZATION_LOSS = "normalization_loss"
    CONTEXT_PROJECTION_LOSS = "context_projection_loss"
    QUALIFICATION_UNCERTAIN = "qualification_uncertain"
    TRUE_NO_SIGNAL = "true_no_signal"
    MISSING_PRIMARY_DATA = "missing_primary_data"


class GapRecoveryAction(StrEnum):
    """Ações de recuperação orientadas pela causa exata."""

    REPROCESS_LOCAL_DATA = "reprocess_local_data"
    REPROJECT_CONTEXT = "reproject_context"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    EXPAND_SEARCH_SCOPE = "expand_search_scope"
    REQUEST_PRIMARY_DATA = "request_primary_data"
    ACCEPT_ABSENCE_OF_SIGNAL = "accept_absence_of_signal"
    STOP_DECLARED_LIMITATION = "stop_declared_limitation"


class ResearchGap(BaseModel):
    """Diagnóstico tipado de lacuna de evidência com ação recomendada e custo."""

    feature_name: str
    description: str
    cause: GapCause
    recommended_action: GapRecoveryAction
    rationale: str
    reproducible_without_cost: bool = False


FEATURE_CAPABILITY_MAP: dict[str, set[str]] = {
    "market_median_price_brl": {"web_crawler", "google_search"},
    "monthly_search_volume": {"google_trends"},
    "average_interest": {"google_trends"},
    "open_jobs_count": {"linkedin_jobs"},
    "ad_count": {"meta_ads"},
    "social_mentions_count": {"youtube_comments", "instagram", "tiktok"},
}


CAPABILITY_EVIDENCE_TYPE_MAP: dict[str, set[str]] = {
    "google_trends": {"TRENDS"},
    "google_search": {"SEARCH_VOLUME", "OFFER"},
    "web_crawler": {"OFFER"},
    "linkedin_jobs": {"JOB_MARKET"},
    "meta_ads": {"PAID_COMPETITION"},
    "youtube_comments": {"SOCIAL_VOICE"},
    "instagram": {"SOCIAL_VOICE"},
    "tiktok": {"SOCIAL_VOICE"},
}


def classify_research_gaps(
    features: EvidenceFeatureSet,
    runs: list[dict[str, Any]] | None = None,
    evidences: list[dict[str, Any]] | None = None,
) -> list[ResearchGap]:
    """Classifica lacunas determinando causa exata e ação correspondente."""
    requirements = [
        (
            ("market_median_price_brl",),
            "Não há preço de oferta educacional comparável, com moeda e periodicidade verificadas.",
        ),
        (
            ("monthly_search_volume", "average_interest"),
            "Não há série de busca ou volume de pesquisa no recorte solicitado.",
        ),
        (("open_jobs_count",), "Não há amostra de vagas pertinentes com localização verificada."),
        (
            ("ad_count",),
            "Não há observação válida de anúncios de ofertas educacionais concorrentes.",
        ),
        (
            ("social_mentions_count",),
            "Não há relatos ou comentários profissionais utilizáveis para confrontar a ementa.",
        ),
    ]

    runs_list = runs or []
    evidences_list = evidences or []
    runs_by_id = {str(r.get("id")): r for r in runs_list if r.get("id")}
    gaps: list[ResearchGap] = []

    for names, message in requirements:
        has_feature = any(
            (feature := features.get(name)) is not None and feature.evidence_ids for name in names
        )
        if has_feature:
            continue

        primary_name = names[0]
        related_capabilities = set()
        for name in names:
            related_capabilities.update(FEATURE_CAPABILITY_MAP.get(name, set()))

        related_evidence_types = set()
        for cap in related_capabilities:
            related_evidence_types.update(CAPABILITY_EVIDENCE_TYPE_MAP.get(cap, set()))

        related_runs = [
            r for r in runs_list if r.get("capability") in related_capabilities
        ]

        # 1. Verificar se dados já foram persistidos em evidences (perda de projeção de contexto)
        matching_evidences = []
        for e in evidences_list:
            ev_type = str(e.get("evidence_type") or "").upper()
            run_id = str(e.get("tool_run_id") or "")
            run = runs_by_id.get(run_id)
            if (
                ev_type in related_evidence_types
                or (run and run.get("capability") in related_capabilities)
                or any(
                    cap in str(e.get("source_name") or "") or cap in str(e.get("collector") or "")
                    for cap in related_capabilities
                )
            ):
                matching_evidences.append(e)

        if matching_evidences:
            gaps.append(
                ResearchGap(
                    feature_name=primary_name,
                    description=message,
                    cause=GapCause.CONTEXT_PROJECTION_LOSS,
                    recommended_action=GapRecoveryAction.REPROJECT_CONTEXT,
                    rationale="Evidência existe na base persistida, mas não chegou à projeção de features.",
                    reproducible_without_cost=True,
                )
            )
            continue

        # 2. Verificar runs existentes da capacidade correspondente
        if related_runs:
            # Perda de normalização: coletou bruto mas perdeu no parser
            normalization_loss_run = next(
                (
                    r
                    for r in related_runs
                    if r.get("raw_items_count", 0) > 0 and r.get("valid_items_count", 0) == 0
                ),
                None,
            )
            if normalization_loss_run:
                gaps.append(
                    ResearchGap(
                        feature_name=primary_name,
                        description=message,
                        cause=GapCause.NORMALIZATION_LOSS,
                        recommended_action=GapRecoveryAction.REPROCESS_LOCAL_DATA,
                        rationale="A ferramenta retornou registros brutos, mas foram descartados ou não mapeados pelo normalizador.",
                        reproducible_without_cost=True,
                    )
                )
                continue

            # Falha técnica de provedor / timeout
            failed_run = next(
                (r for r in related_runs if r.get("status") in {"FAILED", "PARTIAL"} or r.get("error_code")),
                None,
            )
            if failed_run:
                gaps.append(
                    ResearchGap(
                        feature_name=primary_name,
                        description=message,
                        cause=GapCause.SOURCE_FAILURE,
                        recommended_action=GapRecoveryAction.RETRY_WITH_BACKOFF,
                        rationale=f"A execução da ferramenta falhou com erro: {failed_run.get('error_code') or 'falha de execução'}.",
                        reproducible_without_cost=False,
                    )
                )
                continue

            # Ausência real de sinal no mercado
            empty_run = next(
                (
                    r
                    for r in related_runs
                    if r.get("status") == "EMPTY"
                    or (r.get("parameters") or {}).get("observation_status") == "observed_empty"
                ),
                None,
            )
            if empty_run:
                gaps.append(
                    ResearchGap(
                        feature_name=primary_name,
                        description=message,
                        cause=GapCause.TRUE_NO_SIGNAL,
                        recommended_action=GapRecoveryAction.ACCEPT_ABSENCE_OF_SIGNAL,
                        rationale="A busca foi executada corretamente e não encontrou ocorrências no mercado para este recorte.",
                        reproducible_without_cost=True,
                    )
                )
                continue

        # 3. Caso não haja runs: capacidade não consultada ou não suportada
        gaps.append(
            ResearchGap(
                feature_name=primary_name,
                description=message,
                cause=GapCause.TRUE_NO_SIGNAL,
                recommended_action=GapRecoveryAction.EXPAND_SEARCH_SCOPE,
                rationale="Nenhuma consulta foi realizada para esta dimensão.",
                reproducible_without_cost=False,
            )
        )

    return gaps


def research_gaps(features: EvidenceFeatureSet) -> list[str]:
    """Interface legada mantendo compatibilidade com código existente."""
    return [gap.description for gap in classify_research_gaps(features)]
