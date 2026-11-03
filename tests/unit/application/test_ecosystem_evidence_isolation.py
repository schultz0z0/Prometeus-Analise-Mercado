"""Testes unitários de isolamento determinístico entre concorrentes educacionais, seguradoras do radar e própria instituição."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.application.pricing_reference import build_price_reference
from prometeus.application.qualify_market_evidence import EvidenceQualificationService
from prometeus.application.research_scope import (
    match_configured_competitor,
    match_sector_radar_actor,
)
from prometeus.domain.analyses import Analysis
from prometeus.domain.dossiers import (
    DossierClaim,
    DossierComparison,
    DossierFactItem,
    DossierFacts,
    DossierHighlights,
    DossierOutput,
    DossierSection,
)
from prometeus.domain.research import CourseUnderstanding

ENS_CTX: dict[str, object] = {
    "id": "ens",
    "name": "Escola de Negócios e Seguros",
    "domains": ["ens.edu.br", "enscursos.com.br"],
    "competitors": [
        {
            "id": "ibmec",
            "name": "Ibmec",
            "aliases": ["Pós Ibmec"],
            "category": "executive_business",
            "domains": ["ibmec.br", "pos.ibmec.br"],
            "social": {"instagram_handle": "ibmec", "linkedin_scope": "national"},
        },
        {
            "id": "conhecer-seguros",
            "name": "Conhecer Seguros",
            "aliases": ["ConhecerSeguros"],
            "category": "direct_specialist",
            "domains": ["conhecerseguros.com.br"],
            "social": {"instagram_handle": "conhecerseguros", "linkedin_scope": "national"},
        },
    ],
    "sector_radar": [
        {
            "id": "porto-seguro",
            "name": "Porto Seguro",
            "aliases": ["Porto"],
            "priority": "primary",
            "domains": ["portoseguro.com.br"],
            "social": {"instagram_handle": "porto", "linkedin_scope": "national"},
        },
        {
            "id": "mapfre",
            "name": "MAPFRE",
            "aliases": ["MAPFRE Brasil"],
            "priority": "secondary",
            "domains": ["mapfre.com.br"],
            "social": {"instagram_handle": "mapfrebrasil", "linkedin_scope": "global"},
        },
    ],
}


def test_matches_competitor_and_sector_actor_by_domain_and_handle() -> None:
    comp = match_configured_competitor({}, "https://pos.ibmec.br/mba-financas-e-riscos", ENS_CTX)
    assert comp is not None
    assert comp["id"] == "ibmec"

    insurer = match_sector_radar_actor(
        {"ownerUsername": "porto"}, "https://www.instagram.com/p/xyz/", ENS_CTX
    )
    assert insurer is not None
    assert insurer["id"] == "porto-seguro"

    global_insurer = match_sector_radar_actor(
        {}, "https://www.mapfre.com.br/para-voce/", ENS_CTX
    )
    assert global_insurer is not None
    assert global_insurer["id"] == "mapfre"
    assert global_insurer["social"]["linkedin_scope"] == "global"


def test_pricing_reference_excludes_sector_radar_domains_even_if_price_present() -> None:
    audit = build_price_reference(
        course_title="MBA em Inteligência Artificial Aplicada a Seguros",
        level="MBA Executivo",
        institution_name="Escola de Negócios e Seguros",
        institution_domains=["ens.edu.br"],
        sector_radar_domains=["portoseguro.com.br", "bradescoseguros.com.br"],
        internal_prices=[],
        offers=[
            {
                "id": "ev-porto-1",
                "title": "MBA Executivo Seguros e IA Corporativa",
                "source_url": "https://www.portoseguro.com.br/treinamento-corretores",
                "sanitized_data": {
                    "text": "Investimento total: R$ 4.500,00 em São Paulo, Brasil",
                    "total_price": 4500.0,
                    "_qualification": {"accepted": True},
                },
            },
            {
                "id": "ev-ibmec-1",
                "title": "MBA em Inteligência Artificial e Gestão de Riscos em Seguros",
                "source_url": "https://pos.ibmec.br/mba-ia-seguros",
                "sanitized_data": {
                    "text": "Investimento total: R$ 16.800,00 em São Paulo, Brasil",
                    "total_price": 16800.0,
                    "_qualification": {"accepted": True, "actor_role": "configured_competitor"},
                },
            },
        ],
    )
    assert audit["external_count"] == 1
    assert audit["external_mean_brl"] == 16800.0
    assert any(
        x["id"] == "ev-porto-1" and x["reason_code"] == "sector_ecosystem_not_course_offer"
        for x in audit["excluded"]
    )


@pytest.mark.asyncio
async def test_qualification_routes_sector_radar_to_context_and_blocks_direct_competition() -> None:
    porto_row = SimpleNamespace(
        id="ev-porto",
        analysis_id="anl-1",
        evidence_type="OFFER",
        source_name="apify_web_crawler",
        source_url="https://www.portoseguro.com.br/corretores/ia-sinistros",
        collector="apify",
        title="Porto Seguro acelera regulação de sinistros com IA para corretores no Brasil",
        collected_at=datetime.now(UTC),
        sanitized_data={"text": "Solução em São Paulo, Brasil com R$ 3500", "total_price": 3500.0},
    )
    ibmec_row = SimpleNamespace(
        id="ev-ibmec",
        analysis_id="anl-1",
        evidence_type="OFFER",
        source_name="apify_web_crawler",
        source_url="https://pos.ibmec.br/mba-ia-seguros",
        collector="apify",
        title="MBA em IA Aplicada a Seguros e Finanças no Brasil",
        collected_at=datetime.now(UTC),
        sanitized_data={"text": "Curso em São Paulo, Brasil", "total_price": 18000.0},
    )

    session = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [porto_row, ibmec_row]
    exec_mock = MagicMock()
    exec_mock.scalars.return_value = scalars_mock
    session.execute.return_value = exec_mock

    decisions = MagicMock()
    decisions.get_pack.return_value = SimpleNamespace(
        version="1.0.0", model_dump_json=lambda: '{"pack":"market-relevance-v1"}'
    )
    decisions.cache_key_for.return_value = "ck-1"
    decisions.execute_judgment = AsyncMock(
        return_value=SimpleNamespace(
            id="dec-1",
            selected_choice="RELEVANT",
            confidence=0.92,
            requires_human_review=False,
            is_noul=False,
        )
    )

    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em IA Aplicada a Seguros",
        proposal_data={"_institution_context": ENS_CTX},
        correlation_id="corr-1",
    )
    understanding = CourseUnderstanding(
        analysis_id=analysis.id,
        course_title="MBA em IA Aplicada a Seguros",
        subject_domains=["seguros", "inteligência artificial"],
        target_audiences=["corretores de seguros", "analistas de sinistros"],
        geography="Brasil",
        institution_name="Escola de Negócios e Seguros",
        institution_domains=["ens.edu.br"],
    )

    svc = EvidenceQualificationService(session=session, decisions=decisions)
    summary = await svc.qualify(
        analysis, understanding, "corr-1", institution_context=ENS_CTX
    )

    assert summary["accepted"] == 1
    porto_q = porto_row.sanitized_data["_qualification"]
    assert porto_q["actor_role"] == "sector_radar"
    assert porto_q["matched_actor_id"] == "porto-seguro"
    assert porto_q["accepted"] is False
    assert porto_q["context_only"] is True
    assert porto_q["use_assessments"]["direct_competition"]["usable"] is False
    assert (
        porto_q["use_assessments"]["direct_competition"]["rejection_cause"]
        == "sector_ecosystem_not_educational_competitor"
    )
    assert porto_q["use_assessments"]["pricing"]["usable"] is False
    assert "sector_radar" in porto_q["use_for"]

    ibmec_q = ibmec_row.sanitized_data["_qualification"]
    assert ibmec_q["actor_role"] == "configured_competitor"
    assert ibmec_q["matched_actor_id"] == "ibmec"
    assert ibmec_q["accepted"] is True
    assert ibmec_q["use_assessments"]["direct_competition"]["usable"] is True


def test_dossier_verifier_flags_insurer_as_competitor_and_global_linkedin_as_national() -> None:
    facts = DossierFacts(
        analysis_id="anl-1",
        course_name="MBA em IA Aplicada a Seguros",
        target_audience="Corretores e Gestores de Seguros",
        viability_score=80.0,
        coverage_score=0.9,
        confidence_score=0.85,
        recommendation="APPROVED",
        pillar_summaries={"competitive_landscape": 78.0},
        items=[
            DossierFactItem(
                evidence_id="ev-1",
                source_type="SOCIAL_VOICE",
                title="Perfil MAPFRE Global",
                key_metrics={
                    "actor_role": "sector_radar",
                    "matched_actor_name": "MAPFRE",
                    "linkedin_scope": "global",
                },
                summary="Publicação institucional MAPFRE",
            )
        ],
        analysis_audit={
            "declared_offer": {"institution": "Escola de Negócios e Seguros"},
            "sector_radar_actors": ["Porto Seguro", "Bradesco Seguros", "MAPFRE"],
            "global_social_actors": ["MAPFRE", "Zurich Seguros"],
        },
    )
    dossier = DossierOutput(
        analysis_id="anl-1",
        prompt_version="dossier-v1",
        model_name="test-model",
        facts_hash=facts.compute_facts_hash(),
        executive_summary="Síntese executiva apoiada em evidências.",
        executive_summary_claim_ids=["c-1"],
        sections=[
            DossierSection(
                section_id="sec-market",
                title="Concorrência, Ementa, Público e Viabilidade de Preço",
                target_audience="executive",
                content="Análise de riscos e concorrentes para alunos.",
                claim_ids=["c-1"],
            )
        ],
        claims=[
            DossierClaim(
                claim_id="c-1",
                statement="A MAPFRE possui 1.245.338 seguidores no Brasil em seu LinkedIn, validando vagas e preço.",
                evidence_ids=["ev-1"],
            )
        ],
        highlights=DossierHighlights(
            competitors=[DossierComparison(label="Porto Seguro", claim_ids=["c-1"])],
            pros=["c-1"],
            cons=["c-1"],
        ),
    )

    review = DossierVerifier().verify_senior_analytical_quality(dossier, facts)
    issue_codes = {issue["code"] for issue in review.issues}
    assert "sector_actor_as_direct_competitor" in issue_codes
    assert "global_social_metric_as_national" in issue_codes
