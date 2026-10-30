"""Telemetria de chamadas reais de modelo: modelo efetivo, tentativas, uso e custo (tarefa 0.3)."""

from __future__ import annotations

import json

import httpx

from prometeus.domain.execution_envelope import CostStatus, TokenUsage, capture_provider_calls
from prometeus.domain.ports.decision_model import DecisionPack, DecisionType, ModelIdentity
from prometeus.infrastructure.jev.client import TypeSafeJEVClient
from prometeus.infrastructure.llm.client import ChatGPTPlanGenerativeClient, OpenAIGenerativeClient
from prometeus.infrastructure.llm.decision_adapter import LLMDecisionAdapter


async def test_chat_completions_records_effective_model_and_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "gpt-4o-mini-2024-07-18",
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 2, "total_tokens": 13},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = OpenAIGenerativeClient(api_key="k", model="gpt-4o-mini", http_client=http_client)
        with capture_provider_calls() as calls:
            assert await client.generate_text("p") == "ok"
    [call] = calls
    assert call.provider == "openai_chat_completions"
    assert call.model == "gpt-4o-mini-2024-07-18"
    assert call.attempts == 1
    assert call.usage == TokenUsage(input_tokens=11, output_tokens=2, total_tokens=13)
    assert call.cost.status is CostStatus.UNAVAILABLE
    assert call.cost.amount_usd is None


async def test_responses_stream_records_usage_from_completed_event() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        completed = {
            "type": "response.completed",
            "response": {
                "model": "gpt-account-model-2026",
                "usage": {"input_tokens": 40, "output_tokens": 4, "total_tokens": 44},
            },
        }
        stream = "\n".join(
            [
                'data: {"type":"response.output_text.delta","delta":"ok"}',
                "data: " + json.dumps(completed),
                "",
            ]
        )
        return httpx.Response(200, text=stream, headers={"content-type": "text/event-stream"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ChatGPTPlanGenerativeClient(
            access_token="t", model="gpt-account-model", http_client=http_client
        )
        with capture_provider_calls() as calls:
            assert await client.generate_text("p") == "ok"
    [call] = calls
    assert call.provider == "chatgpt_plan_responses"
    assert call.model == "gpt-account-model-2026"
    assert call.usage == TokenUsage(input_tokens=40, output_tokens=4, total_tokens=44)
    assert call.cost.status is CostStatus.UNAVAILABLE
    assert call.cost.source == "chatgpt_plan_quota_not_priced"


async def test_responses_stream_without_usage_keeps_usage_unknown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        stream = (
            'data: {"type":"response.output_text.delta","delta":"ok"}\n'
            'data: {"type":"response.completed"}\n'
        )
        return httpx.Response(200, text=stream, headers={"content-type": "text/event-stream"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ChatGPTPlanGenerativeClient(access_token="t", model="m", http_client=http_client)
        with capture_provider_calls() as calls:
            await client.generate_text("p")
    assert calls[0].usage is None
    assert calls[0].model == "m"


async def test_jev_records_attempts_and_pinned_model() -> None:
    responses = iter([httpx.Response(503), httpx.Response(200, json={"choice": "A", "confidence": 0.9})])

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    pack = DecisionPack(
        pack_id="p", decision_type=DecisionType.CHOICE, question="q", options=["A", "B"]
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TypeSafeJEVClient(
            api_key="secret", model="jev-2026.1", max_retries=2, http_client=http_client
        )
        with capture_provider_calls() as calls:
            await client.execute_choice(pack, {})
    [call] = calls
    assert call.provider == "typesafe_jev"
    assert call.model == "jev-2026.1"
    assert call.attempts == 2
    assert call.usage is None
    assert call.cost.status is CostStatus.UNAVAILABLE
    assert client.model_identity() == ModelIdentity(
        provider="typesafe_jev", model="jev-2026.1", mode="jev"
    )


def test_llm_adapter_identity_and_versions_follow_configured_model() -> None:
    llm = OpenAIGenerativeClient(api_key="secret-key-value", model="gpt-config")
    adapter = LLMDecisionAdapter(llm)
    assert adapter.model_identity() == ModelIdentity(
        provider="OpenAIGenerativeClient", model="gpt-config", mode="traditional_llm"
    )
    versions = adapter.component_versions("market-relevance-v1", {"source": "apify_linkedin_jobs"})
    assert versions["decision_prompt"]
    assert len(versions["local_guidance_sha256"]) == 64
    assert "secret-key-value" not in json.dumps(versions)
