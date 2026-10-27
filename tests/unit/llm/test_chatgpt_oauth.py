from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from prometeus.infrastructure.llm.codex_oauth import (
    DIRECT_USAGE_SCOPE,
    ChatGPTCredentials,
    ChatGPTCredentialStore,
    build_chatgpt_auth_url,
    list_chatgpt_models,
    refresh_chatgpt_tokens,
)


def test_auth_url_uses_official_dynamic_registration_contract(tmp_path: Path) -> None:
    result = build_chatgpt_auth_url(
        host_id="urn:uuid:11111111-1111-4111-8111-111111111111",
    )

    parsed = urlparse(result["auth_url"])
    query = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "auth.openai.com"
    assert parsed.path == "/api/accounts/authorize"
    assert query["client_id"] == ["dynamic_agent_client"]
    assert query["redirect_uri"] == ["http://127.0.0.1:1455/auth/callback"]
    assert query["resource"] == ["https://api.openai.com/v1"]
    assert DIRECT_USAGE_SCOPE in query["scope"][0].split()
    assert query["code_challenge_method"] == ["S256"]
    assert query["agent_name_hint"] == ["Prometeus"]


def test_credential_store_is_atomic_and_never_serializes_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "chatgpt" / "credentials.json"
    credentials = ChatGPTCredentials(
        access_token="access-secret",
        refresh_token="refresh-secret",
        id_token="id-secret",
        expires_at=2_000_000_000.0,
        scopes=(DIRECT_USAGE_SCOPE, "openid"),
        client_id="oaiapp_real",
        subject="subject-1",
        email="user@example.com",
        selected_model="gpt-account-model",
    )
    store = ChatGPTCredentialStore(path)

    store.save(credentials)

    assert store.load() == credentials
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["access_token"] == "access-secret"
    assert payload["selected_model"] == "gpt-account-model"
    assert set(payload) == {
        "access_token",
        "refresh_token",
        "id_token",
        "expires_at",
        "scopes",
        "client_id",
        "subject",
        "email",
        "selected_model",
    }


@pytest.mark.asyncio
async def test_refresh_rotates_both_tokens_and_keeps_granted_scope() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode()
        return httpx.Response(
            200,
            json={
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "id_token": "new-id",
                "expires_in": 3600,
                "scope": f"openid {DIRECT_USAGE_SCOPE}",
            },
        )

    old = ChatGPTCredentials(
        access_token="old-access",
        refresh_token="old-refresh",
        id_token="old-id",
        expires_at=1.0,
        scopes=("openid", DIRECT_USAGE_SCOPE),
        client_id="oaiapp_real",
        subject="subject-1",
        email=None,
        selected_model="gpt-account-model",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        refreshed = await refresh_chatgpt_tokens(old, http_client=client)

    assert refreshed.access_token == "new-access"
    assert refreshed.refresh_token == "new-refresh"
    assert refreshed.client_id == old.client_id
    assert refreshed.selected_model == old.selected_model
    assert "grant_type=refresh_token" in str(captured["body"])
    assert "client_id=oaiapp_real" in str(captured["body"])
    assert "scope=" not in str(captured["body"])


@pytest.mark.asyncio
async def test_model_discovery_keeps_only_list_visible_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer real-access"
        return httpx.Response(
            200,
            json={
                "models": [
                    {"slug": "gpt-visible", "display_name": "Visible", "visibility": "list"},
                    {"slug": "gpt-hidden", "display_name": "Hidden", "visibility": "hidden"},
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        models = await list_chatgpt_models("real-access", http_client=client)

    assert models == [{"slug": "gpt-visible", "display_name": "Visible"}]
