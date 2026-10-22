"""Testes de contrato para TypeSafeJEVClient utilizando httpx.MockTransport."""

import json

import httpx
import pytest

from prometeus.domain.ports.decision_model import (
    DecisionPack,
    DecisionType,
)
from prometeus.infrastructure.jev.client import (
    JEVServiceUnavailableError,
    TypeSafeJEVClient,
)


@pytest.fixture
def choice_pack() -> DecisionPack:
    return DecisionPack(
        pack_id="taxonomy-v1",
        decision_type=DecisionType.CHOICE,
        question="Área do curso?",
        options=["SEGUROS_E_RESSEGUROS", "OUTROS"],
        review_threshold=0.80,
    )


@pytest.fixture
def score_pack() -> DecisionPack:
    return DecisionPack(
        pack_id="syllabus-fit-v1",
        decision_type=DecisionType.SCORE,
        question="Nota de ementa?",
        min_score=0.0,
        max_score=100.0,
        review_threshold=0.75,
    )


@pytest.mark.asyncio
async def test_typesafe_client_choice_success(choice_pack: DecisionPack) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/judgments/choice"
        assert request.headers.get("Authorization") == "Bearer test-api-key"
        body = json.loads(request.content)
        assert body["pack_id"] == "taxonomy-v1"
        assert body["model"] == "jev-2026.1"

        return httpx.Response(
            200,
            json={
                "selected": "SEGUROS_E_RESSEGUROS",
                "confidence": 0.94,
                "distribution": {"SEGUROS_E_RESSEGUROS": 0.94, "OUTROS": 0.06},
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = TypeSafeJEVClient(
            api_key="test-api-key",
            model="jev-2026.1",
            http_client=http_client,
        )
        result = await client.execute_choice(choice_pack, context={"title": "Seguros"})

    assert result.pack_id == "taxonomy-v1"
    assert result.decision_type == DecisionType.CHOICE
    assert result.selected_choice == "SEGUROS_E_RESSEGUROS"
    assert result.confidence == 0.94
    assert result.requires_human_review is False
    assert result.is_noul is False


@pytest.mark.asyncio
async def test_typesafe_client_score_success(score_pack: DecisionPack) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/judgments/score"
        return httpx.Response(
            200,
            json={"score": 88.5, "confidence": 0.91},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = TypeSafeJEVClient(api_key="test-key", http_client=http_client)
        result = await client.execute_score(score_pack, context={"syllabus": "completo"})

    assert result.decision_type == DecisionType.SCORE
    assert result.score_value == 88.5
    assert result.confidence == 0.91
    assert result.requires_human_review is False


@pytest.mark.asyncio
async def test_typesafe_client_returns_noul(choice_pack: DecisionPack) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "is_noul": True,
                "reason": "Evidência contraditória e insuficiente",
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = TypeSafeJEVClient(http_client=http_client)
        result = await client.execute_choice(choice_pack, context={})

    assert result.decision_type == DecisionType.NOUL
    assert result.is_noul is True
    assert result.confidence == 0.0
    assert result.requires_human_review is True


@pytest.mark.asyncio
async def test_typesafe_client_retries_and_raises_unavailable(choice_pack: DecisionPack) -> None:
    attempt_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt_count
        attempt_count += 1
        return httpx.Response(503, text="Service Unavailable")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = TypeSafeJEVClient(max_retries=2, http_client=http_client)

        with pytest.raises(
            JEVServiceUnavailableError, match="TypeSafe JEV indisponível após 2 tentativas"
        ):
            await client.execute_choice(choice_pack, context={})

    assert attempt_count == 2


@pytest.mark.asyncio
async def test_typesafe_client_healthcheck() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "healthy"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = TypeSafeJEVClient(http_client=http_client)
        health = await client.healthcheck()

    assert health["status"] == "ok"
    assert health["model"] == "jev-2026.1"
    assert "latency_ms" in health
