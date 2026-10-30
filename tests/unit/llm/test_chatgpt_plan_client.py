import json
import time
from pathlib import Path

import httpx
import pytest

from prometeus.infrastructure.llm.client import ChatGPTPlanGenerativeClient
from prometeus.infrastructure.llm.codex_oauth import (
    DIRECT_USAGE_SCOPE,
    ChatGPTCredentials,
    ChatGPTCredentialStore,
)


async def test_oauth_structured_generation_sends_strict_schema_to_responses():
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            text='data: {"type":"response.output_text.delta","delta":"{\\"ok\\":true}"}\ndata: {"type":"response.completed"}\n',
            headers={"content-type": "text/event-stream"},
        )

    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ChatGPTPlanGenerativeClient(
            access_token="test", model="account-model", http_client=http_client
        )
        result = await client.generate_structured("Test", system_prompt="JSON", schema=schema)
    assert json.loads(result) == {"ok": True}
    assert captured["text"]["format"] == {
        "type": "json_schema",
        "name": "prometeus_dossier",
        "strict": True,
        "schema": schema,
    }


@pytest.mark.asyncio
async def test_chatgpt_plan_client_uses_streaming_responses_contract() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        captured["payload"] = json.loads(request.content)
        stream = "\n".join(
            [
                'data: {"type":"response.output_text.delta","delta":"resposta "}',
                'data: {"type":"response.output_text.delta","delta":"real"}',
                'data: {"type":"response.completed","response":{"id":"resp-real"}}',
                "",
            ]
        )
        return httpx.Response(200, text=stream, headers={"content-type": "text/event-stream"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ChatGPTPlanGenerativeClient(
            access_token="oauth-access-token",
            model="gpt-account-model",
            reasoning_effort="high",
            http_client=http_client,
        )
        text = await client.generate_text("Analise", system_prompt="Use somente fatos")

    assert text == "resposta real"
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["authorization"] == "Bearer oauth-access-token"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["store"] is False
    assert payload["stream"] is True
    assert payload["instructions"] == "Use somente fatos"
    assert payload["input"] == [{"role": "user", "content": "Analise"}]
    assert "temperature" not in payload


@pytest.mark.asyncio
async def test_chatgpt_plan_client_requires_completed_nonempty_response() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text='data: {"type":"response.output_text.delta","delta":"parcial"}\n',
            headers={"content-type": "text/event-stream"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ChatGPTPlanGenerativeClient(
            access_token="oauth-access-token",
            model="gpt-account-model",
            http_client=http_client,
        )
        with pytest.raises(Exception, match="response.completed"):
            await client.generate_text("Analise")


@pytest.mark.asyncio
async def test_chatgpt_plan_client_refreshes_expired_credentials_before_inference(
    tmp_path: Path,
) -> None:
    requests: list[tuple[str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((str(request.url), request.headers.get("authorization")))
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(
                200,
                json={
                    "access_token": "fresh-access",
                    "refresh_token": "fresh-refresh",
                    "id_token": "fresh-id",
                    "expires_in": 3600,
                    "scope": f"openid {DIRECT_USAGE_SCOPE}",
                },
            )
        return httpx.Response(
            200,
            text=(
                'data: {"type":"response.output_text.delta","delta":"validado"}\n'
                'data: {"type":"response.completed","response":{"id":"resp-real"}}\n'
            ),
            headers={"content-type": "text/event-stream"},
        )

    store = ChatGPTCredentialStore(tmp_path / "credentials.json")
    store.save(
        ChatGPTCredentials(
            access_token="expired-access",
            refresh_token="old-refresh",
            id_token="old-id",
            expires_at=time.time() - 1,
            scopes=(DIRECT_USAGE_SCOPE,),
            client_id="oaiapp_real",
            subject="subject-1",
            email=None,
            selected_model="gpt-account-model",
        )
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ChatGPTPlanGenerativeClient(
            access_token="expired-access",
            model="gpt-account-model",
            http_client=http_client,
            credential_store=store,
        )
        result = await client.generate_text("Valide")

    assert result == "validado"
    assert requests[-1][1] == "Bearer fresh-access"
    assert store.load() is not None
    assert store.load().refresh_token == "fresh-refresh"  # type: ignore[union-attr]
