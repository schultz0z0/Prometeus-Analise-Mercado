from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

import prometeus.entrypoints.rest.app as app_module
from prometeus.infrastructure.llm.codex_oauth import DIRECT_USAGE_SCOPE, OAuthTokenResult


@pytest.mark.asyncio
async def test_simulated_chatgpt_authorization_is_permanently_disabled() -> None:
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/auth/chatgpt/authorize")

    assert response.status_code == 410
    assert "simulado removido" in response.json()["detail"]
    assert "access_token" not in response.text


@pytest.mark.asyncio
async def test_official_callback_validates_model_and_real_inference_before_persisting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential_path = tmp_path / "credentials.json"
    monkeypatch.setenv("CHATGPT_CREDENTIALS_PATH", str(credential_path))
    persisted_env: dict[str, str] = {}

    async def fake_exchange(**kwargs: str) -> OAuthTokenResult:
        assert kwargs["client_id"] == "oaiapp_issued"
        assert kwargs["nonce"]
        return OAuthTokenResult(
            access_token="real-access",
            refresh_token="real-refresh",
            id_token="real-id",
            expires_in=3600,
            scopes=("openid", DIRECT_USAGE_SCOPE),
            client_id="oaiapp_issued",
            subject="subject-1",
            email="user@example.com",
        )

    async def fake_models(_token: str) -> list[dict[str, str]]:
        return [{"slug": "gpt-account-model", "display_name": "Account model"}]

    async def fake_generate(self: object, prompt: str, **_kwargs: object) -> str:
        assert "OAuth Prometeus validado" in prompt
        return "OAuth Prometeus validado."

    monkeypatch.setattr(app_module, "exchange_chatgpt_code", fake_exchange)
    monkeypatch.setattr(app_module, "list_chatgpt_models", fake_models)
    monkeypatch.setattr(app_module.ChatGPTPlanGenerativeClient, "generate_text", fake_generate)
    monkeypatch.setattr(app_module, "_persist_env_updates", persisted_env.update)

    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        auth_response = await client.get("/v1/auth/chatgpt/url")
        auth_url = auth_response.json()["auth_url"]
        state = parse_qs(urlparse(auth_url).query)["state"][0]
        callback = await client.get(
            "/auth/callback",
            params={"code": "code-real", "state": state, "client_id": "oaiapp_issued"},
        )

    assert callback.status_code == 200
    assert "Conexão validada com sucesso" in callback.text
    assert credential_path.is_file()
    assert persisted_env["GEN_LLM_PROVIDER"] == "chatgpt_oauth"
    assert persisted_env["GEN_LLM_MODEL"] == "gpt-account-model"
    assert persisted_env["CHATGPT_ACCESS_TOKEN"] == ""


def test_persist_env_updates_falls_back_to_direct_write_on_permission_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GEN_LLM_PROVIDER=openai\nGEN_LLM_MODEL=gpt-4o\n", encoding="utf-8")
    monkeypatch.setattr(app_module, "_env_path", lambda: env_file)

    original_write_text = Path.write_text

    def failing_write_text(self: Path, *args: object, **kwargs: object) -> int:
        if ".tmp" in self.name:
            raise PermissionError(13, "Permission denied: '.env.tmp'")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", failing_write_text)

    app_module._persist_env_updates(
        {"GEN_LLM_PROVIDER": "chatgpt_oauth", "GEN_LLM_MODEL": "gpt-6.1-sol"}
    )

    content = env_file.read_text(encoding="utf-8")
    assert "GEN_LLM_PROVIDER=chatgpt_oauth" in content
    assert "GEN_LLM_MODEL=gpt-6.1-sol" in content


def test_persist_env_updates_falls_back_to_direct_write_on_replace_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GEN_LLM_PROVIDER=openai\n", encoding="utf-8")
    monkeypatch.setattr(app_module, "_env_path", lambda: env_file)

    def failing_replace(self: Path, target: Path) -> None:
        raise OSError(16, "Device or resource busy")

    monkeypatch.setattr(Path, "replace", failing_replace)

    app_module._persist_env_updates({"GEN_LLM_PROVIDER": "chatgpt_oauth"})

    content = env_file.read_text(encoding="utf-8")
    assert "GEN_LLM_PROVIDER=chatgpt_oauth" in content


@pytest.mark.asyncio
async def test_official_callback_succeeds_even_when_env_file_cannot_be_persisted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential_path = tmp_path / "credentials.json"
    monkeypatch.setenv("CHATGPT_CREDENTIALS_PATH", str(credential_path))

    async def fake_exchange(**kwargs: str) -> OAuthTokenResult:
        return OAuthTokenResult(
            access_token="real-access",
            refresh_token="real-refresh",
            id_token="real-id",
            expires_in=3600,
            scopes=("openid", DIRECT_USAGE_SCOPE),
            client_id="oaiapp_issued",
            subject="subject-1",
            email="user@example.com",
        )

    async def fake_models(_token: str) -> list[dict[str, str]]:
        return [{"slug": "gpt-account-model", "display_name": "Account model"}]

    async def fake_generate(self: object, prompt: str, **_kwargs: object) -> str:
        return "OAuth Prometeus validado."

    def failing_persist(_updates: dict[str, str]) -> None:
        raise PermissionError(13, "Permission denied: '.env.tmp'")

    monkeypatch.setattr(app_module, "exchange_chatgpt_code", fake_exchange)
    monkeypatch.setattr(app_module, "list_chatgpt_models", fake_models)
    monkeypatch.setattr(app_module.ChatGPTPlanGenerativeClient, "generate_text", fake_generate)
    monkeypatch.setattr(app_module, "_persist_env_updates", failing_persist)

    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        auth_response = await client.get("/v1/auth/chatgpt/url")
        auth_url = auth_response.json()["auth_url"]
        state = parse_qs(urlparse(auth_url).query)["state"][0]
        callback = await client.get(
            "/auth/callback",
            params={"code": "code-real", "state": state, "client_id": "oaiapp_issued"},
        )

    assert callback.status_code == 200
    assert "Conexão validada com sucesso" in callback.text
    assert credential_path.is_file()
