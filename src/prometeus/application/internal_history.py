"""IPD institucional por família, com comparáveis e observações rastreáveis.

Ranking é calculado em código. Sem grade ou coorte suficiente não se inventa
aderência curricular nem referência estatística.
"""

from __future__ import annotations

import math
import re
import statistics
import unicodedata
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.application.evidence_features import EvidenceFeatureSet, VerifiedFeature
from prometeus.application.skill_registry import SkillRegistry
from prometeus.domain.analyses import Analysis
from prometeus.domain.research import CourseUnderstanding
from prometeus.infrastructure.db.models import HistoricalCourseModel, HistoricalFunnelModel


def _plain(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()


def normalize_family(value: str) -> str:
    """Preserva a família, sem misturar graduação com pós-graduação."""
    normalized = _plain(value).replace("_", " ")
    if re.search(r"\bmba\b|\bpos\b|especializa|lato sensu", normalized):
        return "pos_mba"
    if "graduacao" in normalized or "bacharel" in normalized or "tecnolog" in normalized:
        return "graduacao"
    if "speed" in normalized:
        return "speed_training"
    if "habilita" in normalized:
        return "habilitacao"
    if "certifica" in normalized:
        return "certificacao_avancada"
    if "extens" in normalized:
        return "extensao"
    if "imers" in normalized:
        return "imersao"
    if "qualifica" in normalized or "aperfeico" in normalized or "capacita" in normalized:
        return "qualificacao_tecnica"
    return normalized.strip().replace(" ", "_")


def _tokens(value: str) -> set[str]:
    stop = {
        "para",
        "como",
        "curso",
        "cursos",
        "mba",
        "executivo",
        "pos",
        "graduacao",
        "lato",
        "sensu",
        "online",
        "avancada",
        "avancado",
        "com",
        "das",
        "dos",
        "uma",
        "por",
        "nas",
        "nos",
        "extensao",
        "extensivo",
        "especializacao",
        "aperfeicoamento",
        "capacitacao",
        "treinamento",
        "imersao",
        "certificacao",
        "qualificacao",
        "habilitacao",
        "formacao",
        "presencial",
        "hibrido",
        "ead",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", _plain(value))
        if len(token) >= 3 and token not in stop
    }


def percentile_rank(value: float, reference: list[float]) -> float:
    """Posto médio dos empates com extremos em 0 e 100 (n >= 2)."""
    if len(reference) < 2:
        raise ValueError("Percentil exige pelo menos duas observações de referência.")
    lower = sum(item < value for item in reference)
    tied = sum(item == value for item in reference)
    if tied == 0:
        raise ValueError("O valor deve pertencer à coorte de referência.")
    return round(100 * (lower + (tied - 1) / 2) / (len(reference) - 1), 4)


def _closed_complete(record: HistoricalFunnelModel) -> bool:
    return (
        record.data_complete is True
        and record.cohort_status.upper()
        in {"COMPLETED", "CLOSED", "CANCELLED_LOW_QUORUM", "CANCELLED", "CANCELED"}
        and all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in (record.leads, record.applicants, record.enrolled)
        )
        and record.enrolled <= record.applicants <= record.leads
    )


class InternalHistoryService:
    def __init__(self, session: AsyncSession, decisions: object | None = None) -> None:
        self.session = session
        self.decisions = decisions

    async def build(
        self,
        analysis: Analysis,
        understanding: CourseUnderstanding,
        correlation_id: str = "none",
    ) -> tuple[EvidenceFeatureSet, dict[str, Any]]:
        family = normalize_family(understanding.level or analysis.proposal_data.get("level", ""))
        courses = list(
            (
                await self.session.execute(
                    select(HistoricalCourseModel).where(
                        HistoricalCourseModel.tenant_id == analysis.tenant_id
                    )
                )
            ).scalars()
        )
        courses = [
            course
            for course in courses
            if normalize_family(course.family or course.category) == family
        ]
        audit: dict[str, Any] = {
            "method": "ipd-family-percentile-v1",
            "family": family,
            "reference_n": 0,
            "reference_period": None,
            "comparables": [],
            "observed_prices": [],
            "limitations": [],
            "percentile_convention": "midrank_0_100",
            "weights": {"leads": 0.2, "applicants": 0.3, "enrolled": 0.5},
            "skill_snapshots": [
                skill.snapshot() for skill in SkillRegistry().for_stage("internal_comparables")
            ],
        }
        if not courses:
            audit["limitations"].append("Não há cursos históricos da mesma família na instituição.")
            return EvidenceFeatureSet(features={}), audit
        records = list(
            (
                await self.session.execute(
                    select(HistoricalFunnelModel).where(
                        HistoricalFunnelModel.course_id.in_([course.id for course in courses])
                    )
                )
            ).scalars()
        )
        closed = [record for record in records if _closed_complete(record)]
        if len(closed) != len(records):
            audit["limitations"].append(
                "Ofertas abertas, sem status de fechamento, incompletas ou com funil inconsistente não entram na referência de IPD."
            )
        if not closed:
            audit["limitations"].append(
                "Não há observações completas e encerradas para calcular o IPD."
            )
            return EvidenceFeatureSet(features={}), audit
        # Última janela comum observada: um curso contribui uma vez, sem premiar
        # o curso que acumulou mais edições em períodos diferentes.
        period = max(record.period for record in closed)
        audit["reference_period"] = period
        by_course = {record.course_id: record for record in closed if record.period == period}
        reference = [course for course in courses if course.id in by_course]
        audit["reference_n"] = len(reference)
        target = _tokens(
            " ".join(
                [
                    understanding.course_title,
                    *understanding.subject_domains,
                    *understanding.learning_outcomes,
                ]
            )
        )
        proposal = analysis.proposal_data or {}
        curriculum = _tokens(
            str(proposal.get("curriculum_text") or proposal.get("curriculum") or "")
        )
        ranked: list[tuple[float, HistoricalCourseModel, float, float | None]] = []
        for course in reference:
            theme = _tokens(" ".join([course.name, *(course.tags or [])]))
            shared = target & theme
            theme_fit = len(shared) / len(target | theme) if target | theme else 0.0
            historical_curriculum = _tokens(
                " ".join([course.curriculum_text or "", *(course.curriculum_modules or [])])
            )
            curriculum_fit = (
                len(curriculum & historical_curriculum) / len(curriculum | historical_curriculum)
                if curriculum and historical_curriculum
                else None
            )
            if not shared or (curriculum_fit is not None and curriculum_fit <= 0):
                continue
            fit = theme_fit if curriculum_fit is None else 0.65 * theme_fit + 0.35 * curriculum_fit
            if fit < 0.15:
                continue
            ranked.append((fit, course, theme_fit, curriculum_fit))
        selected = sorted(ranked, key=lambda item: (-item[0], item[1].id))[:3]
        if not selected:
            audit["limitations"].append(
                "Nenhum curso da família possui proximidade temática e curricular verificável suficiente."
            )
            return EvidenceFeatureSet(features={}), audit
        if any(item[3] is None for item in selected):
            audit["limitations"].append(
                "Grade curricular ausente na proposta ou em comparáveis: seleção por metadados temáticos, sem alegar comparação de grades."
            )
        adequate = len(reference) >= 3
        if not adequate:
            audit["limitations"].append(
                "A coorte possui menos de três cursos da família: IPD indisponível por insuficiência de referência."
            )
        for fit, course, theme_fit, curriculum_fit in selected:
            record = by_course[course.id]
            percentiles = (
                {
                    metric: percentile_rank(
                        float(getattr(record, metric)),
                        [float(getattr(by_course[c.id], metric)) for c in reference],
                    )
                    for metric in ("leads", "applicants", "enrolled")
                }
                if adequate
                else {}
            )
            ipd = (
                round(
                    0.2 * percentiles["leads"]
                    + 0.3 * percentiles["applicants"]
                    + 0.5 * percentiles["enrolled"],
                    2,
                )
                if adequate
                else None
            )
            audit["comparables"].append(
                {
                    "course_id": course.id,
                    "name": course.name,
                    "category": course.category,
                    "family": family,
                    "theme_fit": round(theme_fit, 4),
                    "curriculum_fit": round(curriculum_fit, 4)
                    if curriculum_fit is not None
                    else None,
                    "selection_fit": round(fit, 4),
                    "reason": "Mesma família e proximidade de tema e grade"
                    if curriculum_fit is not None
                    else "Mesma família e proximidade de tema; grade não fornecida",
                    "period": period,
                    "leads": record.leads,
                    "applicants": record.applicants,
                    "enrolled": record.enrolled,
                    "percentiles": percentiles,
                    "ipd_score": ipd,
                    "evidence_ids": [course.id, record.id],
                }
            )
            price = record.average_ticket_brl
            if (
                record.price_period == "total"
                and price is not None
                and math.isfinite(price)
                and price > 0
            ):
                audit["observed_prices"].append(
                    {
                        "course_id": course.id,
                        "name": course.name,
                        "category": course.category,
                        "family": family,
                        "tags": course.tags or [],
                        "total_brl": price,
                        "price_brl": price,
                        "price_period": "total",
                        "currency": "BRL",
                        "source": "internal",
                        "period": period,
                        "evidence_ids": [course.id, record.id],
                    }
                )
        if not audit["observed_prices"]:
            audit["limitations"].append(
                "Comparáveis internos sem preço total com periodicidade explícita; valores de unidade desconhecida não são convertidos."
            )
        if not adequate:
            return EvidenceFeatureSet(features={}), audit
        grades = sum(item[3] is not None for item in selected) / len(selected)
        mean_fit = statistics.mean(item[0] for item in selected)
        fit_scale = min(1.0, mean_fit / 0.35)
        confidence = round(0.9 * min(1.0, len(reference) / 10) * (0.6 + 0.4 * grades) * fit_scale, 4)
        evidence_ids = [eid for item in audit["comparables"] for eid in item["evidence_ids"]]
        value = round(statistics.mean(item["ipd_score"] for item in audit["comparables"]), 2)
        return EvidenceFeatureSet(
            features={
                "internal_ipd_score": VerifiedFeature(
                    "internal_ipd_score", value, evidence_ids, "ipd_20_30_50_family_percentile"
                ),
                "internal_ipd_confidence": VerifiedFeature(
                    "internal_ipd_confidence",
                    confidence,
                    evidence_ids,
                    "ipd_reference_and_curriculum_completeness",
                ),
            }
        ), audit
