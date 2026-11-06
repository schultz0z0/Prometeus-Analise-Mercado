from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.sector_radar import SectorRadarService
from prometeus.domain.configuration import load_tenant_config
from prometeus.entrypoints.rest.app import app
from prometeus.infrastructure.db.models import Base, SectorRadarSnapshotModel
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


@pytest.mark.asyncio
async def test_get_ens_ecosystem_returns_ten_competitors_ten_insurers_and_no_secrets(
    client: httpx.AsyncClient,
) -> None:
    resp = await client.get("/v1/tenants/ens/ecosystem")
    assert resp.status_code == 200
    assert resp.headers.get("Content-Security-Policy") == "default-src 'self'"

    data = resp.json()
    assert data["tenant_id"] == "ens"
    assert data["institution_name"] == "Escola de Negócios e Seguros"
    assert len(data["competitors"]) == 10
    assert len(data["sector_radar"]) == 10
    assert data["allow_extra_intake_competitors"] is True
    assert data["radar_ttl_hours"] == 168

    comp_ids = {item["id"] for item in data["competitors"]}
    assert {
        "conhecer-seguros",
        "fgv",
        "ibmec",
        "fipecafi",
        "fia",
        "insper",
        "estacio",
        "esa-oab",
        "fiap",
        "alura",
    } == comp_ids

    radar_status = data["radar_status"]
    assert isinstance(radar_status, dict)
    assert radar_status["has_snapshot"] is False
    assert radar_status["signals_count"] == 0

    serialized = json.dumps(data).lower()
    for secret_term in ("apify_token", "openai_api_key", "access_token", "client_secret"):
        assert secret_term not in serialized


@pytest.mark.asyncio
async def test_get_legacy_tenant_ecosystem_returns_empty_lists(
    client: httpx.AsyncClient,
) -> None:
    resp = await client.get(
        "/v1/tenants/infnet/ecosystem",
        headers={"Authorization": "Bearer test-infnet-key-12345678901234567890"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == "infnet"
    assert data["competitors"] == []
    assert data["sector_radar"] == []


@pytest.mark.asyncio
async def test_get_unknown_or_invalid_tenant_ecosystem_returns_404(
    client: httpx.AsyncClient,
) -> None:
    resp_unknown = await client.get("/v1/tenants/instituicao-inexistente/ecosystem")
    assert resp_unknown.status_code == 403

    resp_traversal = await client.get("/v1/tenants/..%2Fsecret/ecosystem")
    assert resp_traversal.status_code in {403, 404}


@pytest.mark.asyncio
async def test_post_sector_radar_refresh_returns_fresh_snapshot_and_404_for_unknown(
    client: httpx.AsyncClient,
    test_session: AsyncSession,
) -> None:
    ens_cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    cfg_hash = SectorRadarService._config_hash(list(ens_cfg.ecosystem.sector_radar))
    now = datetime.now(UTC)

    snapshot = SectorRadarSnapshotModel(
        id="rdr-test-ens-01",
        tenant_id="ens",
        status="READY",
        collected_at=now,
        expires_at=now + timedelta(hours=168),
        monitored_actors_count=10,
        covered_actors=["porto-seguro", "tokio-marine"],
        signals=[
            {
                "signal_id": "sig-01",
                "actor_id": "porto-seguro",
                "insurer_name": "Porto Seguro",
                "priority": "primary",
                "channel_label": "Web Institucional",
                "scope_badge": "Brasil",
                "theme_detected": "IA, Automação & Subscrição",
                "market_or_broker_pain": "Automação de subscrição e vistoria digital para corretores",
                "source_url": "https://www.portoseguro.com.br/noticias/ia",
                "collected_at": now.isoformat(),
            }
        ],
        trending_themes=["IA, Automação & Subscrição"],
        spent_usd=0.12,
        config_hash=cfg_hash,
        error_summary=None,
    )
    test_session.add(snapshot)
    await test_session.commit()

    resp_eco = await client.get("/v1/tenants/ens/ecosystem")
    assert resp_eco.status_code == 200
    assert resp_eco.json()["radar_status"]["has_snapshot"] is True
    assert resp_eco.json()["radar_status"]["is_fresh"] is True
    assert resp_eco.json()["radar_status"]["signals_count"] == 1

    resp_refresh = await client.post(
        "/v1/tenants/ens/sector-radar/refresh",
        json={"force": False, "max_budget_usd": 1.0},
    )
    assert resp_refresh.status_code == 200
    refresh_data = resp_refresh.json()
    assert refresh_data["tenant_id"] == "ens"
    assert refresh_data["status"] == "READY"
    assert refresh_data["signals_count"] == 1
    assert refresh_data["spent_usd"] == 0.12

    resp_404 = await client.post("/v1/tenants/instituicao-inexistente/sector-radar/refresh")
    assert resp_404.status_code == 403


def test_intake_view_renders_automatic_ecosystem_panel_and_preserves_optional_seed_input() -> None:
    ens_cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    ens_eco = {
        "tenant_id": "ens",
        "institution_name": ens_cfg.institution.display_name,
        "allow_extra_intake_competitors": True,
        "competitors": [c.model_dump(mode="json") for c in ens_cfg.ecosystem.competitors],
        "sector_radar": [s.model_dump(mode="json") for s in ens_cfg.ecosystem.sector_radar],
        "radar_status": {
            "has_snapshot": True,
            "is_fresh": True,
            "status": "READY",
            "signals_count": 6,
        },
    }
    source = Path("web/js/views/intake-view.js").resolve().as_uri()
    script = f"""import {{renderIntakeView}} from {json.dumps(source)};
let input=''; for await (const chunk of process.stdin) input+=chunk;
const payload=JSON.parse(input);
console.log(renderIntakeView({{getState:()=>payload}}));"""

    ens_state = {
        "tenants": [{"id": "ens", "name": "ENS — Escola de Negócios e Seguros"}],
        "currentTenantId": "ens",
        "tenantEcosystems": {"ens": ens_eco},
    }
    html_ens = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        input=json.dumps(ens_state),
        encoding="utf-8",
        capture_output=True,
        check=True,
    ).stdout

    assert "intake-ecosystem-panel" in html_ens
    assert "Ecossistema Monitorado Automaticamente" in html_ens
    assert "Conhecer Seguros" in html_ens
    assert "Ibmec" in html_ens
    assert "Estácio" in html_ens
    assert "Porto Seguro" in html_ens
    assert "Tokio Marine" in html_ens
    assert "intake-extra-seed-details" in html_ens
    assert 'id="course-competitors"' in html_ens

    infnet_state = {
        "tenants": [{"id": "infnet", "name": "Instituto Infnet"}],
        "currentTenantId": "infnet",
        "tenantEcosystems": {
            "infnet": {"tenant_id": "infnet", "competitors": [], "sector_radar": []}
        },
    }
    html_infnet = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        input=json.dumps(infnet_state),
        encoding="utf-8",
        capture_output=True,
        check=True,
    ).stdout

    assert "intake-ecosystem-panel" not in html_infnet
    assert 'id="course-competitors"' in html_infnet


@pytest.mark.asyncio
async def test_post_sector_radar_refresh_blocks_when_kill_switch_active(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KILL_SWITCH_ACTIVE", "true")
    resp = await client.post(
        "/v1/tenants/ens/sector-radar/refresh",
        json={"force": True, "max_budget_usd": 1.0},
    )
    assert resp.status_code == 503
    assert "kill switch" in resp.json()["detail"].lower()
