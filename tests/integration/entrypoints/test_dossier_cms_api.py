"""Testes de integração da API REST para hidratação do CMS de 9 subpáginas e persistência SQL de revisões por área."""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.entrypoints.rest.app import app
from prometeus.infrastructure.db.models import (
    AnalysisModel,
    Base,
    DossierModel,
    MarketEvidenceModel,
    ScoringResultModel,
)
from prometeus.infrastructure.db.session import get_db_session


@pytest.fixture
async def test_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(test_session: AsyncSession) -> httpx.AsyncClient:
    async def override_session():
        yield test_session

    app.dependency_overrides[get_db_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        headers={"Authorization": "Bearer test-admin-key-12345678901234567890"},
        base_url="http://test",
    ) as c:
        yield c
    app.dependency_overrides.clear()


async def _seed_legacy_completed_analysis(session: AsyncSession, analysis_id: str, tenant_id: str = "ens") -> None:
    analysis = AnalysisModel(
        id=analysis_id,
        tenant_id=tenant_id,
        course_name="MBA em Gestão de Riscos e Seguros",
        status="COMPLETED",
        recommendation="APPROVED_WITH_ADJUSTMENTS",
        proposal_data={
            "area": "Seguros",
            "level": "MBA",
            "modality": "EAD Live",
            "ticket": 11900.0,
            "price_period": "total",
            "workload_hours": 360,
        },
    )
    scoring = ScoringResultModel(
        id=f"scr-{analysis_id}",
        analysis_id=analysis_id,
        profile_id="portfolio-v2",
        viability_score=77.8,
        partial_score=77.8,
        coverage_score=0.85,
        confidence_score=0.83,
        recommendation="APPROVED_WITH_ADJUSTMENTS",
        pillar_scores={
            "internal_history": {"raw_score": 88.0, "is_present": True},
            "paid_competition": {"raw_score": 74.0, "is_present": True},
            "search_and_media": {"raw_score": 80.0, "is_present": True},
            "employability": {"raw_score": 76.0, "is_present": True},
            "syllabus_fit": {"raw_score": 82.0, "is_present": True},
            "pricing": {"raw_score": 68.0, "is_present": True},
        },
        gate_details={},
        is_experimental=True,
    )
    ev_id = f"ev-{analysis_id[:8]}"
    evidence = MarketEvidenceModel(
        id=ev_id,
        analysis_id=analysis_id,
        evidence_type="JOB_MARKET",
        source_name="linkedin_jobs",
        source_url="https://linkedin.com/jobs/view/1",
        collector="apify",
        title="Especialista em Riscos e Seguros",
        raw_payload={},
        sanitized_data={"open_jobs_count": 19},
        content_hash=f"hash-{analysis_id[:8]}",
        quality_score=0.9,
        cost_usd=0.01,
    )
    # Simula um dossiê legado sem `cms_pages` salvo no presentation
    dossier = DossierModel(
        id=f"dos-{analysis_id}",
        analysis_id=analysis_id,
        prompt_version="dossier-v1",
        model_name="gpt-5.4",
        facts_hash="hash-legacy-123",
        status="VERIFIED",
        executive_summary="Demanda consistente para formação executiva em riscos e seguros.",
        sections=[
            {
                "section_id": "sec-exec",
                "title": "Parecer Executivo",
                "target_audience": "executive",
                "content": "Mercado receptivo com vagas ativas.",
                "claim_ids": ["CLM-1"],
            }
        ],
        claims=[
            {
                "claim_id": "CLM-1",
                "statement": "Foram observadas 19 vagas para especialistas em riscos.",
                "claim_type": "QUANTITATIVE",
                "evidence_ids": [ev_id],
                "support_level": "OBSERVED",
                "verification_status": "VERIFIED",
            }
        ],
        presentation={
            "contract_version": 2,
            "highlights": {
                "pros": ["CLM-1"],
                "cons": [],
                "action_recommendations": [
                    {
                        "area": "marketing",
                        "action": "Destacar empregabilidade na campanha de captação.",
                        "claim_ids": ["CLM-1"],
                        "priority": "high",
                        "status": "proposed",
                    }
                ],
                "validation_criteria": [],
            },
            "limitations": ["Custos fixos da turma não informados."],
        },
        cost_usd=0.02,
    )
    session.add_all([analysis, scoring, evidence, dossier])
    await session.commit()


@pytest.mark.asyncio
async def test_legacy_dossier_hydrates_cms_pages_and_supports_area_reviews_persistence(
    client: httpx.AsyncClient,
    test_session: AsyncSession,
) -> None:
    analysis_id = "11111111-2222-3333-4444-555555555555"
    await _seed_legacy_completed_analysis(test_session, analysis_id, tenant_id="ens")

    # 1. GET /v1/analyses/{id}/dossier deve hidratar cms_pages com as 9 subpáginas
    resp = await client.get(f"/v1/analyses/{analysis_id}/dossier")
    assert resp.status_code == 200
    dossier_data = resp.json()
    cms_pages = dossier_data["presentation"]["cms_pages"]
    assert cms_pages["schema_version"] == 1
    assert len(cms_pages["tabs"]) == 9
    assert cms_pages["pages"]["overview"]["ivo_score"] == 78
    assert cms_pages["pages"]["revisions"]["overall_progress"]["percent"] == 0

    # 2. POST /v1/analyses/{id}/area-reviews para Marketing e Comercial
    rev1 = await client.post(
        f"/v1/analyses/{analysis_id}/area-reviews",
        json={
            "area": "marketing",
            "status": "APPROVED",
            "reviewer_name": "Ana Ribeiro",
            "comment": "Cenário de demanda validado para campanha do 1º semestre.",
        },
    )
    assert rev1.status_code == 200
    rev1_body = rev1.json()
    assert rev1_body["overall_progress"]["approved_count"] == 1
    assert rev1_body["overall_progress"]["percent"] == 25

    rev2 = await client.post(
        f"/v1/analyses/{analysis_id}/area-reviews",
        json={
            "area": "produto",
            "status": "IN_REVIEW",
            "reviewer_name": "Bruno Castro",
            "comment": "Validando carga horária dos módulos práticos.",
        },
    )
    assert rev2.status_code == 200

    rev3 = await client.post(
        f"/v1/analyses/{analysis_id}/area-reviews",
        json={
            "area": "comercial",
            "status": "APPROVED",
            "reviewer_name": "Carla Menezes",
            "comment": "Projeção comercial validada.",
        },
    )
    assert rev3.status_code == 200
    rev3_body = rev3.json()
    assert rev3_body["overall_progress"]["approved_count"] == 2
    assert rev3_body["overall_progress"]["percent"] == 50

    # 3. GET /v1/analyses?tenant_id=ens deve refletir as revisões persistidas no banco
    list_resp = await client.get("/v1/analyses?tenant_id=ens")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    revisions_page = items[0]["dossier"]["presentation"]["cms_pages"]["pages"]["revisions"]
    assert revisions_page["overall_progress"]["percent"] == 50
    assert len(revisions_page["comments_feed"]) == 3
    assert revisions_page["version_history"][0]["version"] == "v1.3"

    # 4. Isolamento multi-tenant: análise de outro tenant não permite submissão pelo principal atual
    other_id = "99999999-8888-7777-6666-555555555555"
    await _seed_legacy_completed_analysis(test_session, other_id, tenant_id="other-tenant")
    forbidden_rev = await client.post(
        f"/v1/analyses/{other_id}/area-reviews",
        json={
            "area": "financeiro",
            "status": "APPROVED",
            "reviewer_name": "Diego Martins",
            "comment": "Tentativa cross-tenant.",
        },
    )
    assert forbidden_rev.status_code in {403, 404}
