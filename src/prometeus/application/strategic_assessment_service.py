"""Serviço de aplicação e regras determinísticas para parecer estratégico e SWOT/TOWS (Tarefa 4.3).

Garante que regras analíticas da ENS sejam estritamente validadas em código:
1. Lacuna de dados não vira fraqueza comercial.
2. Nome ENS não prova reputação ou qualidade docente do novo curso.
3. Vaga não vira demanda por curso.
4. Crescimento de prêmio de seguro não vira potencial de matrícula.
5. Fonte própria não vira concorrente externo.
"""

from __future__ import annotations

import unicodedata

from prometeus.domain.strategic_assessment import (
    MarketFinding,
    StrategicAssessment,
    SWOTDimension,
    SWOTItem,
)


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def validate_data_gap_is_not_weakness(item: SWOTItem) -> None:
    """Lacuna de dados de pesquisa não pode ser classificada como fraqueza comercial."""
    if item.dimension == SWOTDimension.WEAKNESS:
        plain_text = _plain(item.statement + " " + item.quote_or_datapoint)
        gap_indicators = [
            "ausencia de dados",
            "sem dados",
            "dados insuficientes",
            "lacuna de pesquisa",
            "hasdata=false",
            "nao foi possivel coletar",
            "falta de informacao",
        ]
        if any(ind in plain_text for ind in gap_indicators):
            raise ValueError(
                "Lacuna de dados de pesquisa não pode ser classificada como fraqueza comercial do curso; "
                "deve ser registrada como lacuna/risco informacional."
            )


def validate_ens_brand_does_not_prove_course_quality(item: SWOTItem) -> None:
    """A marca ou tradição institucional não comprova a qualidade docente do curso novo."""
    if item.dimension == SWOTDimension.STRENGTH:
        plain_text = _plain(item.statement)
        if "ens" in plain_text and any(
            w in plain_text for w in ["comprovam", "garantem", "provam", "asseguram"]
        ) and any(w in plain_text for w in ["qualidade docente", "excelencia docente", "qualidade academica"]):
            raise ValueError(
                "A marca ou tradição institucional não comprova a qualidade docente ou adequação "
                "pedagógica de um curso novo sem avaliação específica."
            )


def validate_job_posting_is_not_course_demand(finding_or_item: MarketFinding | SWOTItem) -> None:
    """Vagas de emprego representam demanda do mercado profissional, não demanda de matrícula."""
    text = (
        finding_or_item.finding
        if isinstance(finding_or_item, MarketFinding)
        else finding_or_item.statement
    )
    plain_text = _plain(text)
    if any(w in plain_text for w in ["vaga", "vagas", "job", "linkedin"]):
        if any(w in plain_text for w in ["garantem demanda", "comprovam demanda de", "matriculas garantidas", "viram demanda"]):
            raise ValueError(
                "Vagas de emprego representam demanda do mercado de trabalho por competências profissionais, "
                "não demanda direta ou garantia de matrículas no curso."
            )


def validate_insurance_premium_growth_is_not_enrollment(finding_or_item: MarketFinding | SWOTItem) -> None:
    """Crescimento de prêmio de seguros (SUSEP/CNseg) é contexto macro, não potencial de matrícula."""
    text = (
        finding_or_item.finding
        if isinstance(finding_or_item, MarketFinding)
        else finding_or_item.statement
    )
    plain_text = _plain(text)
    if any(w in plain_text for w in ["susep", "cnseg", "premio", "premios emitidos"]):
        if any(w in plain_text for w in ["potencial direto de matricula", "potencial de matricula", "multiplicador de aluno"]):
            raise ValueError(
                "O crescimento de prêmios emitidos no setor segurador (dados SUSEP/CNseg) é contexto "
                "macroeconômico e não constitui potencial direto de matrículas."
            )


def validate_own_source_is_not_external_competitor(item: SWOTItem) -> None:
    """Ofertas ou canais da própria instituição não viram concorrência externa."""
    if item.dimension == SWOTDimension.THREAT:
        source_text = _plain(item.evidence_source + " " + item.statement)
        if any(d in source_text for d in ["ens.edu.br", "enscursos.com.br", "propria instituicao", "escola de negocios e seguros"]):
            raise ValueError(
                "Cursos ou páginas da própria instituição são contexto institucional interno e "
                "não podem ser classificados como ameaça ou concorrência externa."
            )


class StrategicAssessmentService:
    """Serviço para consolidação e verificação de integridade de pareceres estratégicos."""

    def validate_assessment(self, assessment: StrategicAssessment) -> StrategicAssessment:
        """Executa as validações das 5 regras ontológicas e analíticas da ENS."""
        for item in assessment.swot_items:
            validate_data_gap_is_not_weakness(item)
            validate_ens_brand_does_not_prove_course_quality(item)
            validate_job_posting_is_not_course_demand(item)
            validate_insurance_premium_growth_is_not_enrollment(item)
            validate_own_source_is_not_external_competitor(item)

        for finding in assessment.market_findings:
            validate_job_posting_is_not_course_demand(finding)
            validate_insurance_premium_growth_is_not_enrollment(finding)

        return assessment
