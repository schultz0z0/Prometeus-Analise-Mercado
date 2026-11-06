"""Controles reais de acesso, sem bypass de autenticação nem credenciais externas."""

import importlib
import json

import httpx
import pytest

from prometeus.domain.configuration import AppSettings

api = importlib.import_module("prometeus.entrypoints.rest.app")


@pytest.fixture
def access_settings(monkeypatch, tmp_path):
    records = [
        {
            "key": "test-admin-key-12345678901234567890",
            "subject": "operator",
            "tenant_id": "ens",
            "role": "admin",
        },
        {
            "key": "test-reader-key-1234567890123456789",
            "subject": "auditor",
            "tenant_id": "ens",
            "role": "reader",
        },
    ]
    monkeypatch.setenv("SERVICE_API_KEYS", json.dumps(records))
    monkeypatch.setenv("AUTH_ADMIN_KEY_PATH", str(tmp_path / "admin.key"))
    settings = AppSettings(
        _env_file=None, APP_ENV="test", CHATGPT_CREDENTIALS_PATH=str(tmp_path / "missing.json")
    )
    monkeypatch.setattr(api, "AppSettings", lambda: settings)
    monkeypatch.setattr(api, "_persist_env_updates", lambda updates: None)
    return records


async def test_anonymous_cannot_read_configuration(access_settings):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/settings")
        assert response.status_code == 401


async def test_reader_cannot_change_configuration(access_settings):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {access_settings[1]['key']}"},
    ) as client:
        response = await client.post("/v1/settings", json={"apify_max_charge": 10})
        assert response.status_code == 403


async def test_key_cannot_access_another_institution(access_settings):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {access_settings[0]['key']}"},
    ) as client:
        response = await client.get("/v1/tenants/infnet/ecosystem")
        assert response.status_code == 403
        response = await client.post(
            "/v1/tenants/infnet/sector-radar/refresh", json={"tenant_id": "ens"}
        )
        assert response.status_code == 403
        response = await client.get("/v1/analyses?tenant_id=infnet&tenant_id=ens")
        assert response.status_code == 403


async def test_browser_session_is_httponly_and_rejects_cross_origin_write(access_settings):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app), base_url="http://test"
    ) as client:
        login = await client.post(
            "/v1/session/login", json={"access_key": access_settings[0]["key"]}
        )
        assert login.status_code == 200
        assert "httponly" in login.headers["set-cookie"].lower()
        assert "samesite=strict" in login.headers["set-cookie"].lower()
        assert (await client.get("/v1/session")).json()["subject"] == "operator"
        forbidden = await client.post(
            "/v1/settings",
            json={"apify_max_charge": 10},
            headers={"Origin": "https://attacker.example"},
        )
        assert forbidden.status_code == 403
        await client.post("/v1/session/logout")
        assert (await client.get("/v1/settings")).status_code == 401


async def test_invalid_key_and_forged_cookie_are_rejected(access_settings):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app), base_url="http://test"
    ) as client:
        response = await client.post("/v1/session/login", json={"access_key": "invalid"})
        assert response.status_code == 401
        response = await client.get("/v1/settings", headers={"Cookie": "prometeus_session=forged"})
        assert response.status_code == 401


async def test_healthcheck_stays_public(access_settings):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app), base_url="http://test"
    ) as client:
        assert (await client.get("/health/live")).status_code == 200


async def test_resource_tenant_and_recorded_identity_are_enforced(access_settings):
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from prometeus.domain.analyses import Analysis
    from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
    from prometeus.infrastructure.db.models import Base, HumanDecisionModel
    from prometeus.infrastructure.db.session import get_db_session

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        own = Analysis.create(tenant_id="ens", course_name="Own", correlation_id="test")
        other = Analysis.create(tenant_id="infnet", course_name="Other", correlation_id="test")
        await AnalysisRepository(session).save(own)
        await AnalysisRepository(session).save(other)
        await session.commit()

        async def isolated_session():
            yield session

        api.app.dependency_overrides[get_db_session] = isolated_session
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=api.app),
                base_url="http://test",
                headers={"Authorization": f"Bearer {access_settings[0]['key']}"},
            ) as client:
                for suffix in ("", "/dossier", "/status"):
                    assert (await client.get(f"/v1/analyses/{other.id}{suffix}")).status_code == 403
                assert (await client.post(f"/v1/analyses/{other.id}/cancel")).status_code == 403
                response = await client.post(
                    f"/v1/analyses/{own.id}/decisions",
                    json={
                        "user_id": "forged",
                        "user_role": "director",
                        "decision": "APPROVED",
                        "rationale": "Test",
                    },
                )
                assert response.status_code == 201
                recorded = (await session.execute(select(HumanDecisionModel))).scalar_one()
                assert recorded.user_id == "operator"
                assert recorded.user_role == "admin"
        finally:
            api.app.dependency_overrides.clear()
    await engine.dispose()
