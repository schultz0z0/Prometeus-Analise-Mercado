"""Mapeadores e higienizadores de dados para a API institucional da ENS.

Realiza tradução para os contratos canônicos, cálculo de qualidade e
garantia absoluta de minimização de dados (LGPD: zero PII no core).
"""

from __future__ import annotations

import logging
from typing import Any

from prometeus.domain.ports.institutional_data import (
    CanonicalCourse,
    FinancialMetrics,
    FunnelMetrics,
)

logger = logging.getLogger(__name__)

# Campos expressamente proibidos de trafegar para o core (LGPD)
PROHIBITED_EXACT_PII = {"cpf", "rg", "email", "telefone", "celular", "endereco"}
PROHIBITED_SUBSTRING_PII = {
    "cpf",
    "email",
    "telefone",
    "celular",
    "nome_aluno",
    "nome_candidato",
    "endereco",
}


def sanitize_raw_record(record: dict[str, Any]) -> dict[str, Any]:
    """Descarta ativamente qualquer campo que possa conter PII identificável de alunos."""
    sanitized: dict[str, Any] = {}
    for k, v in record.items():
        k_lower = k.lower()
        if k_lower in PROHIBITED_EXACT_PII:
            continue
        if any(pii in k_lower for pii in PROHIBITED_SUBSTRING_PII):
            continue
        sanitized[k] = v
    return sanitized


def map_ens_course(raw: dict[str, Any]) -> CanonicalCourse:
    """Mapeia registro de curso da ENS para o modelo canônico."""
    clean = sanitize_raw_record(raw)
    external_id = str(
        clean.get("codigo_curso") or clean.get("cod_curso") or clean.get("id_curso") or ""
    ).strip()
    name = str(clean.get("nome_curso") or clean.get("nome") or "Curso Sem Nome").strip()
    category = str(clean.get("categoria") or clean.get("tipo") or "Geral").strip()
    modality = str(clean.get("modalidade") or "online").strip().lower()

    workload = 0
    raw_workload = clean.get("carga_horaria") or clean.get("horas")
    if raw_workload is not None:
        try:
            workload = int(raw_workload)
        except (ValueError, TypeError):
            workload = 0

    return CanonicalCourse(
        external_id=external_id,
        name=name,
        category=category,
        modality=modality,
        workload_hours=workload,
        status="active",
        target_audience=[],
        tags=[t.strip().lower() for t in category.split() if len(t) > 2],
    )


def map_ens_leads(data: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    """Mapeia contagem agregada de leads indexada por (curso_id, periodo)."""
    leads_map: dict[tuple[str, str], int] = {}
    for item in data:
        clean = sanitize_raw_record(item)
        cid = str(clean.get("codigo_curso") or clean.get("cod_curso") or "").strip()
        periodo = str(clean.get("periodo") or "default").strip()
        total = int(clean.get("total_leads") or clean.get("leads") or 0)
        if cid:
            leads_map[(cid, periodo)] = leads_map.get((cid, periodo), 0) + total
    return leads_map


def map_ens_inscritos(data: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    """Mapeia contagem agregada de inscritos indexada por (curso_id, periodo)."""
    inscritos_map: dict[tuple[str, str], int] = {}
    for item in data:
        clean = sanitize_raw_record(item)
        cid = str(clean.get("cod_curso") or clean.get("codigo_curso") or "").strip()
        periodo = str(clean.get("periodo_letivo") or clean.get("periodo") or "default").strip()
        total = int(clean.get("qtd_inscritos") or clean.get("inscritos") or 0)
        if cid:
            inscritos_map[(cid, periodo)] = inscritos_map.get((cid, periodo), 0) + total
    return inscritos_map


def map_ens_matriculados(
    data: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], FinancialMetrics]]:
    """Mapeia matriculados e métricas financeiras indexadas por (curso_id, periodo)."""
    matriculados_map: dict[tuple[str, str], int] = {}
    financial_map: dict[tuple[str, str], FinancialMetrics] = {}

    for item in data:
        clean = sanitize_raw_record(item)
        cid = str(clean.get("id_curso") or clean.get("codigo_curso") or "").strip()
        periodo = str(clean.get("semestre") or clean.get("periodo") or "default").strip()
        total = int(
            clean.get("matriculas_confirmadas")
            or clean.get("matriculas_efetivas")
            or clean.get("matriculados")
            or 0
        )
        if cid:
            matriculados_map[(cid, periodo)] = matriculados_map.get((cid, periodo), 0) + total

            ticket = float(clean.get("ticket_medio_brl") or clean.get("ticket_medio") or 0.0)
            revenue = float(clean.get("faturamento_brl") or clean.get("receita_total") or 0.0)
            cac = clean.get("cac_brl") or clean.get("custo_aquisicao")
            cac_val = float(cac) if cac is not None else None

            financial_map[(cid, periodo)] = FinancialMetrics(
                external_course_id=cid,
                period=periodo,
                average_ticket_brl=ticket,
                total_revenue_brl=revenue,
                acquisition_cost_brl=cac_val,
            )

    return matriculados_map, financial_map


def consolidate_funnel_metrics(
    course_ids: list[str],
    leads_map: dict[tuple[str, str], int],
    inscritos_map: dict[tuple[str, str], int],
    matriculados_map: dict[tuple[str, str], int],
    period: str | None = None,
) -> tuple[list[FunnelMetrics], float, list[str]]:
    """Consolida as três pontas do funil calculando métricas e score de qualidade de dados.

    Retorna: (funnel_metrics, data_quality_score, divergence_warnings).
    """
    all_keys = set(leads_map.keys()) | set(inscritos_map.keys()) | set(matriculados_map.keys())
    metrics_list: list[FunnelMetrics] = []
    warnings: list[str] = []
    penalty = 0.0

    for cid, per in sorted(all_keys):
        if course_ids and cid not in course_ids:
            continue
        if period and per != period:
            continue

        l_count = leads_map.get((cid, per), 0)
        i_count = inscritos_map.get((cid, per), 0)
        m_count = matriculados_map.get((cid, per), 0)

        # Validações de integridade do funil
        if m_count > i_count and i_count > 0:
            msg = f"Divergência no curso {cid} ({per}): matriculados ({m_count}) > inscritos ({i_count})"
            warnings.append(msg)
            logger.warning(msg)
            penalty += 0.15

        if i_count > l_count and l_count > 0:
            msg = f"Divergência no curso {cid} ({per}): inscritos ({i_count}) > leads ({l_count})"
            warnings.append(msg)
            logger.warning(msg)
            penalty += 0.10

        metrics_list.append(
            FunnelMetrics(
                external_course_id=cid,
                period=per,
                leads=l_count,
                applicants=i_count,
                enrolled=m_count,
            )
        )

    quality_score = max(0.0, round(1.0 - penalty, 2))
    return metrics_list, quality_score, warnings
