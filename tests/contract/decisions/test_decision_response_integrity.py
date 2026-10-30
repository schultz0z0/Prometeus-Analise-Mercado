"""Contratos estritos de integridade de resposta para decisões (Tarefa 1.4).

Verifica que respostas com missing choice, unknown label, booleano, NaN/Inf,
negativo, soma inválida, score fora da faixa ou indisponibilidade NUNCA viram
RELEVANT, OBSERVED, score default ou confiança 1.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from prometeus.domain.ports.decision_model import (
    DecisionPack,
    DecisionType,
)
from prometeus.domain.ports.generative_model import GenerativeModelPort
from prometeus.infrastructure.jev.client import (
    JEVError,
    TypeSafeJEVClient,
)
from prometeus.infrastructure.llm.decision_adapter import LLMDecisionAdapter


class MockGenerativeModel(GenerativeModelPort):
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.model = "mock-llm-strict"

    async def generate_keyword_candidates(
        self, course_title: str, description: str, target_audience: str, max_candidates: int = 15
    ) -> list[str]:
        return []

    async def generate_text(
        self, prompt: str, system_prompt: str | None = None, temperature: float = 0.2
    ) -> str:
        return self.response_text

    async def synthesize_dossier(self, facts: Any, prompt_version: str = "dossier-v1") -> Any:
        raise NotImplementedError

    async def revise_dossier(self, facts: Any, draft: Any, verification_report: Any, prompt_version: str = "dossier-v1") -> Any:
        raise NotImplementedError


@pytest.fixture
def choice_pack() -> DecisionPack:
    return DecisionPack(
        pack_id="market-relevance-v1",
        version="1.0.0",
        decision_type=DecisionType.CHOICE,
        question="Avalie a pertinência da evidência",
        options=["RELEVANT", "CONTEXT", "IRRELEVANT", "INCONCLUSIVE"],
        review_threshold=0.75,
    )


@pytest.fixture
def score_pack() -> DecisionPack:
    return DecisionPack(
        pack_id="syllabus-fit-v1",
        version="1.0.0",
        decision_type=DecisionType.SCORE,
        question="Nota de aderência curricular",
        min_score=0.0,
        max_score=100.0,
        review_threshold=0.75,
    )


# --- Testes para LLMDecisionAdapter ---

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_payload,error_match",
    [
        (
            {"confidence": 0.9, "distribution": {"RELEVANT": 1.0}},
            "selected_choice",
        ),
        (
            {"selected_choice": "UNKNOWN_LABEL", "confidence": 0.9, "distribution": {"UNKNOWN_LABEL": 1.0}},
            "não permitida",
        ),
        (
            {"selected_choice": "RELEVANT", "confidence": True, "distribution": {"RELEVANT": 1.0}},
            "booleano",
        ),
        (
            {"selected_choice": "RELEVANT", "confidence": float("nan"), "distribution": {"RELEVANT": 1.0}},
            "finito",
        ),
        (
            {"selected_choice": "RELEVANT", "confidence": float("inf"), "distribution": {"RELEVANT": 1.0}},
            "finito",
        ),
        (
            {"selected_choice": "RELEVANT", "confidence": -0.1, "distribution": {"RELEVANT": 1.0}},
            "entre 0.0 e 1.0",
        ),
        (
            {"selected_choice": "RELEVANT", "confidence": 1.5, "distribution": {"RELEVANT": 1.0}},
            "entre 0.0 e 1.0",
        ),
        (
            {"selected_choice": "RELEVANT", "confidence": 0.9, "distribution": "not_a_dict"},
            "distribution",
        ),
        (
            {"selected_choice": "RELEVANT", "confidence": 0.9, "distribution": {"RELEVANT": 0.5, "CONTEXT": 0.9}},
            "distribuição",
        ),
        (
            {"selected_choice": "RELEVANT", "confidence": 0.9, "distribution": {"INVALID_KEY": 1.0}},
            "distribuição",
        ),
    ],
)
async def test_llm_adapter_rejects_invalid_choice_payloads(
    choice_pack: DecisionPack, invalid_payload: dict[str, Any], error_match: str
) -> None:
    adapter = LLMDecisionAdapter(MockGenerativeModel(json.dumps(invalid_payload)))
    with pytest.raises(ValueError, match=error_match):
        await adapter.execute_choice(choice_pack, {"some": "data"})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_payload,error_match",
    [
        (
            {"confidence": 0.8},
            "score_value",
        ),
        (
            {"score_value": True, "confidence": 0.8},
            "booleano",
        ),
        (
            {"score_value": float("nan"), "confidence": 0.8},
            "finito",
        ),
        (
            {"score_value": float("inf"), "confidence": 0.8},
            "finito",
        ),
        (
            {"score_value": -10.0, "confidence": 0.8},
            "fora da escala",
        ),
        (
            {"score_value": 150.0, "confidence": 0.8},
            "fora da escala",
        ),
        (
            {"score_value": 85.0, "confidence": True},
            "booleano",
        ),
    ],
)
async def test_llm_adapter_rejects_invalid_score_payloads(
    score_pack: DecisionPack, invalid_payload: dict[str, Any], error_match: str
) -> None:
    adapter = LLMDecisionAdapter(MockGenerativeModel(json.dumps(invalid_payload)))
    with pytest.raises(ValueError, match=error_match):
        await adapter.execute_score(score_pack, {"syllabus": "..."})


# --- Testes para TypeSafeJEVClient ---

@pytest.mark.asyncio
async def test_jev_client_never_defaults_missing_choice_to_first_option(
    choice_pack: DecisionPack,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"confidence": 0.9})  # sem choice nem selected

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TypeSafeJEVClient(http_client=http_client)
        with pytest.raises(JEVError, match="choice|selected"):
            await client.execute_choice(choice_pack, {})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_jev_response,error_match",
    [
        ({"choice": "INVALID_OPTION", "confidence": 0.9}, "não permitida"),
        ({"choice": "RELEVANT", "confidence": True}, "booleano"),
        ({"choice": "RELEVANT", "confidence": "nan"}, "finito"),
        ({"choice": "RELEVANT", "confidence": -0.5}, "entre 0.0 e 1.0"),
        ({"choice": "RELEVANT", "confidence": 1.2}, "entre 0.0 e 1.0"),
    ],
)
async def test_jev_client_rejects_corrupted_choice_payloads(
    choice_pack: DecisionPack, invalid_jev_response: dict[str, Any], error_match: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=invalid_jev_response)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TypeSafeJEVClient(http_client=http_client)
        with pytest.raises(JEVError, match=error_match):
            await client.execute_choice(choice_pack, {})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_jev_score,error_match",
    [
        ({"confidence": 0.8}, "score|value"),  # missing score
        ({"score": True, "confidence": 0.8}, "booleano"),
        ({"score": "nan", "confidence": 0.8}, "finito"),
        ({"score": -5.0, "confidence": 0.8}, "fora da escala"),
        ({"score": 105.0, "confidence": 0.8}, "fora da escala"),
    ],
)
async def test_jev_client_rejects_corrupted_score_payloads(
    score_pack: DecisionPack, invalid_jev_score: dict[str, Any], error_match: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=invalid_jev_score)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TypeSafeJEVClient(http_client=http_client)
        with pytest.raises(JEVError, match=error_match):
            await client.execute_score(score_pack, {})
