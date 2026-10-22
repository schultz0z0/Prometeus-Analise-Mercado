"""Testes de contrato para endpoints REST da Fase 07 (Reanálise, Dossiê, Decisões, Outcomes, Cancelamento)."""

import uuid
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.domain.analyses import Analysis
from prometeus.entrypoints.rest.app import app
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, DossierModel
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
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reanalyze_creates_linked_analysis(
    client: httpx.AsyncClient, test_session: AsyncSession
) -> None:
    repo = AnalysisRepository(test_session)
    orig = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Sinistros",
        correlation_id="corr-orig",
        proposal_data={"price": 1200.0},
    )
    await repo.save(orig)
    await test_session.commit()

    response = await client.post(
        f"/v1/analyses/{orig.id}/reanalyze",
        json={"proposal_data": {"price": 950.0, "new_module": "Cyber Insurance"}},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["previous_analysis_id"] == orig.id
    assert data["status"] == "QUEUED"
    assert data["analysis_id"] != orig.id


@pytest.mark.asyncio
async def test_cancel_analysis_flow(client: httpx.AsyncClient, test_session: AsyncSession) -> None:
    repo = AnalysisRepository(test_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Subscrição",
        correlation_id="corr-cancel",
    )
    await repo.save(analysis)
    await test_session.commit()

    # Cancela com sucesso
    response = await client.post(f"/v1/analyses/{analysis.id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"

    # Segunda tentativa deve dar 409 Conflict (já está terminal)
    conflict_resp = await client.post(f"/v1/analyses/{analysis.id}/cancel")
    assert conflict_resp.status_code == 409


@pytest.mark.asyncio
async def test_get_dossier_endpoint(client: httpx.AsyncClient, test_session: AsyncSession) -> None:
    repo = AnalysisRepository(test_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Resseguro",
        correlation_id="corr-dossier",
    )
    await repo.save(analysis)
    await test_session.commit()

    # Sem dossiê ainda -> 404
    not_found = await client.get(f"/v1/analyses/{analysis.id}/dossier")
    assert not_found.status_code == 404

    # Insere dossiê
    dossier = DossierModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        prompt_version="dossier-v1",
        model_name="gpt-4o-mini",
        facts_hash="hash-123",
        status="VERIFIED",
        executive_summary="Resumo de alto nível.",
        sections=[{"section_id": "exec", "title": "Diretoria", "content": "Texto"}],
        claims=[{"claim_id": "CLM-01", "statement": "Claim"}],
        cost_usd=0.005,
        created_at=datetime.now(UTC),
    )
    test_session.add(dossier)
    await test_session.commit()

    resp = await client.get(f"/v1/analyses/{analysis.id}/dossier")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "VERIFIED"
    assert body["executive_summary"] == "Resumo de alto nível."


@pytest.mark.asyncio
async def test_submit_human_decision_endpoint(
    client: httpx.AsyncClient, test_session: AsyncSession
) -> None:
    repo = AnalysisRepository(test_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Regulação de Seguros",
        correlation_id="corr-dec",
    )
    await repo.save(analysis)
    await test_session.commit()

    payload = {
        "user_id": "usr-diretor-01",
        "user_role": "director",
        "decision": "APPROVED",
        "rationale": "Aprovado pelo conselho acadêmico para o semestre 2026.2",
        "adjustments": {"max_students": 50},
    }
    resp = await client.post(f"/v1/analyses/{analysis.id}/decisions", json=payload)
    assert resp.status_code == 201
    assert resp.json()["status"] == "RECORDED"
    assert resp.json()["decision"] == "APPROVED"


@pytest.mark.asyncio
async def test_record_outcome_endpoint(
    client: httpx.AsyncClient, test_session: AsyncSession
) -> None:
    repo = AnalysisRepository(test_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Seguros Rurais",
        correlation_id="corr-out",
    )
    await repo.save(analysis)
    await test_session.commit()

    payload = {
        "external_course_id": "ENS-RURAL-2026",
        "launch_date": "2026-08-01",
        "enrolled_count": 48,
        "leads_count": 320,
        "applicants_count": 80,
        "revenue_brl": 384000.0,
        "notes": "Desempenho superou a meta inicial de 35 alunos.",
    }
    resp = await client.post(f"/v1/analyses/{analysis.id}/outcomes", json=payload)
    assert resp.status_code == 201
    assert resp.json()["status"] == "RECORDED"
    assert resp.json()["enrolled_count"] == 48
