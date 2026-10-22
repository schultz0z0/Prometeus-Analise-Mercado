"""Mapeadores de dados da API institucional do Instituto Infnet para o modelo canônico Prometeus."""

from __future__ import annotations

from typing import Any

from prometeus.domain.ports.institutional_data import (
    CanonicalCourse,
    FinancialMetrics,
    FunnelMetrics,
)


def map_infnet_modality(raw_formato: str) -> str:
    """Normaliza formatos do Infnet (online_ao_vivo, presencial, flex) para o padrão canônico."""
    fmt = (raw_formato or "").lower().strip()
    if "online" in fmt or "vivo" in fmt or "remoto" in fmt:
        return "online"
    if "presencial" in fmt:
        return "presencial"
    if "hibrid" in fmt or "flex" in fmt:
        return "hibrido"
    return "online"


def map_infnet_course(raw: dict[str, Any]) -> CanonicalCourse:
    """Mapeia objeto bruto de curso do Infnet para CanonicalCourse."""
    return CanonicalCourse(
        external_id=str(raw.get("id") or raw.get("curso_id")),
        name=str(raw.get("titulo") or raw.get("nome")),
        category=str(raw.get("escola") or raw.get("departamento") or "Tecnologia"),
        modality=map_infnet_modality(raw.get("formato", "online")),
        workload_hours=int(raw.get("carga_horaria", 0)),
        status="active" if str(raw.get("status_curso", "ativo")).lower() == "ativo" else "archived",
        target_audience=list(raw.get("publico_alvo", [])),
        tags=list(raw.get("habilidades", raw.get("tags", []))),
    )


def map_infnet_funnel(raw: dict[str, Any]) -> FunnelMetrics:
    """Mapeia métricas brutas de captação do Infnet para FunnelMetrics canônico."""
    return FunnelMetrics(
        external_course_id=str(raw.get("curso_id")),
        period=str(raw.get("semestre") or raw.get("periodo")),
        leads=int(raw.get("cadastros", 0)),
        applicants=int(raw.get("candidatos", 0)),
        enrolled=int(raw.get("matriculas", 0)),
    )


def map_infnet_financial(raw: dict[str, Any]) -> FinancialMetrics:
    """Mapeia métricas financeiras brutas do Infnet para FinancialMetrics canônico."""
    return FinancialMetrics(
        external_course_id=str(raw.get("curso_id")),
        period=str(raw.get("semestre") or raw.get("periodo")),
        average_ticket_brl=float(raw.get("ticket_medio", 0.0)),
        total_revenue_brl=float(raw.get("faturamento", 0.0)),
        acquisition_cost_brl=float(raw.get("cac", 0.0)) if "cac" in raw else None,
    )
