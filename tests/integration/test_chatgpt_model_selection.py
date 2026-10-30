import time
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

import prometeus.entrypoints.rest.app as app_module
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.factory import get_generative_model
from prometeus.infrastructure.llm.codex_oauth import (
    DIRECT_USAGE_SCOPE,
    ChatGPTCredentials,
    ChatGPTCredentialStore,
)


@pytest.fixture
def connected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "credentials.json"
    credentials = ChatGPTCredentials(
        access_token="secret-access",
        refresh_token="secret-refresh",
        id_token="secret-id",
        expires_at=time.time() + 3600,
        scopes=("openid", DIRECT_USAGE_SCOPE),
        client_id="oaiapp_real",
        subject="account",
        email="user@example.com",
        selected_model="account-old",
    )
    ChatGPTCredentialStore(path).save(credentials)
    monkeypatch.setenv("CHATGPT_CREDENTIALS_PATH", str(path))
    monkeypatch.setenv("GEN_LLM_PROVIDER", "chatgpt_oauth")
    monkeypatch.setenv("GEN_LLM_MODEL", "account-old")
    monkeypatch.setenv("GEN_LLM_REASONING_EFFORT", "")
    saved = {}

    def persist(updates):
        saved.update(updates)
        for key, value in updates.items():
            monkeypatch.setenv(key, value)

    monkeypatch.setattr(app_module, "_persist_env_updates", persist)

    async def models(_token):
        assert _token == "secret-access"
        return [
            {"slug": "account-old", "display_name": "Anterior"},
            {
                "slug": "account-new",
                "display_name": "Novo",
                "supported_reasoning_efforts": ["low", "high"],
            },
        ]

    monkeypatch.setattr(app_module, "list_chatgpt_models", models)
    return path, credentials, saved


@pytest.mark.asyncio
async def test_model_selection_updates_credentials_env_settings_and_factory(connected):
    path, credentials, saved = connected
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_module.app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/settings",
            json={
                "gen_llm_provider": "chatgpt_oauth",
                "gen_llm_model": "account-new",
                "gen_llm_reasoning_effort": "high",
            },
        )
        current = await client.get("/v1/settings")
    assert response.status_code == 200
    updated = ChatGPTCredentialStore(path).load()
    assert updated == replace(credentials, selected_model="account-new")
    assert saved["GEN_LLM_MODEL"] == "account-new"
    assert current.json()["gen_llm_model"] == "account-new"
    assert current.json()["chatgpt_oauth_model"] == "account-new"
    assert get_generative_model(AppSettings()).model == "account-new"


@pytest.mark.asyncio
async def test_catalog_endpoint_exposes_only_models_and_no_credentials(connected, monkeypatch):
    async def models(_token):
        return [
            {
                "slug": "account-new",
                "display_name": "Novo",
                "access_token": "never-expose",
                "supported_reasoning_efforts": ["low", "high"],
            }
        ]

    monkeypatch.setattr(app_module, "list_chatgpt_models", models)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_module.app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/auth/chatgpt/models")
    assert response.status_code == 200
    assert response.json()["models"] == [
        {
            "slug": "account-new",
            "display_name": "Novo",
            "supported_reasoning_efforts": ["low", "high"],
        }
    ]
    assert "token" not in response.text
    assert "secret" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"gen_llm_model": "invented-model"},
        {"gen_llm_model": "account-new", "gen_llm_reasoning_effort": "max"},
        {"gen_llm_model": "account-new", "gen_llm_reasoning_effort": "nonsense"},
    ],
)
async def test_unavailable_model_or_unsupported_effort_never_changes_credentials(
    connected, payload
):
    path, credentials, saved = connected
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_module.app), base_url="http://test"
    ) as client:
        response = await client.post("/v1/settings", json=payload)
    assert response.status_code == 422
    assert ChatGPTCredentialStore(path).load() == credentials
    assert saved == {}


@pytest.mark.asyncio
async def test_model_catalog_refreshes_expired_session_without_reconnection(connected, monkeypatch):
    path, credentials, _ = connected
    expired = replace(credentials, expires_at=0)
    ChatGPTCredentialStore(path).save(expired)

    async def refresh(old):
        assert old == expired
        return replace(
            old,
            access_token="refreshed-access",
            refresh_token="refreshed-refresh",
            expires_at=time.time() + 3600,
        )

    async def models(token):
        assert token == "refreshed-access"
        return [{"slug": "account-old", "display_name": "Atual"}]

    monkeypatch.setattr(app_module, "refresh_chatgpt_tokens", refresh, raising=False)
    monkeypatch.setattr(app_module, "list_chatgpt_models", models)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_module.app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/auth/chatgpt/models")
    assert response.status_code == 200
    assert ChatGPTCredentialStore(path).load().access_token == "refreshed-access"
    assert "refreshed-access" not in response.text


@pytest.mark.asyncio
async def test_failed_catalog_has_actionable_error_and_does_not_apply_new_model(
    connected, monkeypatch
):
    path, credentials, saved = connected

    async def unavailable(_token):
        raise RuntimeError("provider failure with secret-access")

    monkeypatch.setattr(app_module, "list_chatgpt_models", unavailable)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_module.app), base_url="http://test"
    ) as client:
        response = await client.post("/v1/settings", json={"gen_llm_model": "account-new"})
    assert response.status_code == 502
    assert "secret-access" not in response.text
    assert ChatGPTCredentialStore(path).load() == credentials
    assert saved == {}


@pytest.mark.asyncio
async def test_api_model_save_does_not_override_oauth_selection(connected):
    path, credentials, saved = connected
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_module.app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/settings",
            json={
                "gen_llm_provider": "openai",
                "gen_llm_model": "api-only-model",
            },
        )
    assert response.status_code == 200
    assert saved["GEN_LLM_MODEL"] == "api-only-model"
    assert ChatGPTCredentialStore(path).load() == credentials


@pytest.mark.asyncio
@pytest.mark.parametrize("interleaving", ["token_refresh", "different_account", "newer_selection"])
async def test_failed_settings_persistence_never_restores_stale_tokens_or_another_account(
    connected, monkeypatch, interleaving
):
    from fastapi import HTTPException

    path, original, _ = connected
    store = ChatGPTCredentialStore(path)
    latest = None

    def failing_persist(_updates):
        nonlocal latest
        latest = replace(
            store.load(),
            access_token="rotated-access",
            refresh_token="rotated-refresh",
            id_token="rotated-id",
            expires_at=time.time() + 7200,
            subject="another-account" if interleaving == "different_account" else original.subject,
            selected_model="newer-choice" if interleaving == "newer_selection" else "account-new",
        )
        store.save(latest)
        raise HTTPException(status_code=500, detail="Persistence failed")

    monkeypatch.setattr(app_module, "_persist_env_updates", failing_persist)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_module.app), base_url="http://test"
    ) as client:
        response = await client.post("/v1/settings", json={"gen_llm_model": "account-new"})
    assert response.status_code == 500
    expected_model = (
        original.selected_model if interleaving == "token_refresh" else latest.selected_model
    )
    assert store.load() == replace(latest, selected_model=expected_model)
