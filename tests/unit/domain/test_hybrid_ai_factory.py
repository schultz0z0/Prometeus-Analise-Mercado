"""Testes unitários para o chaveamento automático entre Modo Híbrido e 100% Tradicional."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

import pytest

from prometeus.domain.configuration import AppSettings
from prometeus.domain.ports.decision_model import (
    DecisionPack,
    DecisionType,
)
from prometeus.infrastructure.factory import (
    get_decision_model,
    get_generative_model,
)
from prometeus.infrastructure.jev.client import TypeSafeJEVClient
from prometeus.infrastructure.llm.client import (
    ChatGPTPlanGenerativeClient,
    OpenAIGenerativeClient,
)
from prometeus.infrastructure.llm.codex_oauth import (
    DIRECT_USAGE_SCOPE,
    ChatGPTCredentials,
    ChatGPTCredentialStore,
)
from prometeus.infrastructure.llm.decision_adapter import LLMDecisionAdapter
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


def test_factory_returns_typesafe_jev_when_api_key_provided() -> None:
    """Quando TYPESAFE_API_KEY estiver configurada, deve ativar o Modo Híbrido com JEV."""

    settings = AppSettings(
        AI_MODE="auto",
        TYPESAFE_API_KEY="test_typesafe_secret_123",
        JEV_MODEL="jev-v1.2.0",
    )

    assert settings.is_jev_configured is True

    decision_model = get_decision_model(settings)

    assert isinstance(decision_model, TypeSafeJEVClient)

    assert decision_model.model == "jev-v1.2.0"


def test_factory_automatically_falls_back_to_traditional_llm_when_no_jev() -> None:
    """Quando TYPESAFE_API_KEY estiver vazia, deve chavear automaticamente para a LLM Tradicional."""

    settings = AppSettings(
        TYPESAFE_API_KEY="",
        AI_MODE="auto",
        GEN_LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test-openai",
    )

    assert settings.is_jev_configured is False

    decision_model = get_decision_model(settings)

    assert isinstance(decision_model, LLMDecisionAdapter)

    assert isinstance(decision_model.generative_model, OpenAIGenerativeClient)


def test_factory_rejects_chatgpt_session_token_as_openai_api_credential(tmp_path: Path) -> None:
    """Token de sessão ChatGPT não é tratado como API key da plataforma."""

    settings = AppSettings(
        _env_file=None,
        GEN_LLM_PROVIDER="chatgpt_oauth",
        CHATGPT_ACCESS_TOKEN="sess-chatgpt-oauth-token-xyz",
        OPENAI_BASE_URL="https://api.openai.com/v1",
        GEN_LLM_MODEL="gpt-4o",
        CHATGPT_CREDENTIALS_PATH=str(tmp_path / "credentials.json"),
    )

    assert settings.is_traditional_llm_configured is False

    with pytest.raises(Exception, match="não possui credencial"):
        get_generative_model(settings)


def test_factory_supports_chatgpt_plan_token_with_direct_usage_scope() -> None:

    payload = (
        base64.urlsafe_b64encode(
            json.dumps(
                {
                    "aud": "https://api.openai.com/v1",
                    "scope": "openid resource.invoke chatgpt.tokens.use.direct",
                }
            ).encode()
        )
        .decode()
        .rstrip("=")
    )

    token = f"header.{payload}.signature"

    settings = AppSettings(
        _env_file=None,
        GEN_LLM_PROVIDER="chatgpt_oauth",
        CHATGPT_ACCESS_TOKEN=token,
        GEN_LLM_MODEL="gpt-6.1-sol",
    )

    assert settings.is_traditional_llm_configured is True

    assert isinstance(get_generative_model(settings), ChatGPTPlanGenerativeClient)


def test_factory_prefers_protected_chatgpt_credential_store(tmp_path: Path) -> None:

    credential_path = tmp_path / "chatgpt" / "credentials.json"

    ChatGPTCredentialStore(credential_path).save(
        ChatGPTCredentials(
            access_token="stored-access",
            refresh_token="stored-refresh",
            id_token="stored-id",
            expires_at=time.time() + 3600,
            scopes=(DIRECT_USAGE_SCOPE,),
            client_id="oaiapp_real",
            subject="subject-1",
            email=None,
            selected_model="gpt-from-account",
        )
    )

    settings = AppSettings(
        _env_file=None,
        GEN_LLM_PROVIDER="chatgpt_oauth",
        CHATGPT_ACCESS_TOKEN="",
        CHATGPT_CREDENTIALS_PATH=str(credential_path),
    )

    assert settings.is_traditional_llm_configured is True

    client = get_generative_model(settings)

    assert isinstance(client, ChatGPTPlanGenerativeClient)

    assert client.api_key == "stored-access"

    assert client.model == "gpt-from-account"


@pytest.mark.asyncio
async def test_llm_decision_adapter_evaluates_choice_score_and_noul() -> None:
    """Valida que o LLMDecisionAdapter executa as 3 primitivas (CHOICE, SCORE, NOUL) com parsing estruturado."""

    fake_llm = FakeGenerativeModel()

    adapter = LLMDecisionAdapter(fake_llm)

    # 1. Teste CHOICE

    fake_llm.canned_text = '{"selected_choice": "HIGH_VIABILITY", "confidence": 0.91, "distribution": {"HIGH_VIABILITY": 0.91, "LOW": 0.09}}'

    choice_pack = DecisionPack(
        pack_id="pack_choice_test",
        decision_type=DecisionType.CHOICE,
        question="Qual o nível de viabilidade?",
        options=["HIGH_VIABILITY", "LOW"],
    )

    res_choice = await adapter.evaluate(choice_pack, {"course": "Seguros"})

    assert res_choice.decision_type == DecisionType.CHOICE

    assert res_choice.selected_choice == "HIGH_VIABILITY"

    assert res_choice.confidence == 0.91

    assert res_choice.requires_human_review is False

    # 2. Teste SCORE

    fake_llm.canned_text = (
        '{"score_value": 87.5, "confidence": 0.88, "requires_human_review": false}'
    )

    score_pack = DecisionPack(
        pack_id="pack_score_test",
        decision_type=DecisionType.SCORE,
        question="Pontue a atratividade",
        min_score=0.0,
        max_score=100.0,
    )

    res_score = await adapter.evaluate(score_pack, {"course": "Seguros"})

    assert res_score.decision_type == DecisionType.SCORE

    assert res_score.score_value == 87.5

    assert res_score.confidence == 0.88

    # 3. Teste NOUL (Verdadeiro/Falso)

    fake_llm.canned_text = '{"is_noul": true, "confidence": 0.95}'

    noul_pack = DecisionPack(
        pack_id="pack_noul_test",
        decision_type=DecisionType.NOUL,
        question="Existe demanda no mercado securitário?",
    )

    res_noul = await adapter.evaluate(noul_pack, {"course": "Seguros"})

    assert res_noul.decision_type == DecisionType.NOUL

    assert res_noul.is_noul is True

    assert res_noul.requires_human_review is True


@pytest.mark.asyncio
async def test_llm_decision_adapter_rejects_malformed_choice_instead_of_inventing_default() -> None:

    fake_llm = FakeGenerativeModel(canned_text="resposta sem JSON")

    adapter = LLMDecisionAdapter(fake_llm)

    pack = DecisionPack(
        pack_id="pack_choice_strict",
        decision_type=DecisionType.CHOICE,
        question="Qual opção é sustentada?",
        options=["SUPPORTED", "UNSUPPORTED"],
    )

    with pytest.raises(ValueError, match="JSON válido"):
        await adapter.execute_choice(pack, {"evidence_ids": ["ev-1"]})


def test_factory_propagates_configured_openai_model_and_reasoning_effort() -> None:

    settings = AppSettings(
        GEN_LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test-openai",
        GEN_LLM_MODEL="gpt-4o-mini",
        GEN_LLM_REASONING_EFFORT="high",
    )

    client = get_generative_model(settings)

    assert isinstance(client, OpenAIGenerativeClient)

    assert client.model == "gpt-4o-mini"

    assert client.reasoning_effort == "high"


@pytest.mark.asyncio
async def test_openai_generative_client_payload_reasoning_effort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Garante que reasoning_effort é injetado no payload e 'temperature' é omitida para modelos de raciocínio."""

    import httpx

    captured_payload = {}

    async def mock_post(self: Any, url: str, **kwargs: Any) -> httpx.Response:

        nonlocal captured_payload

        captured_payload = kwargs.get("json", {})

        request = httpx.Request("POST", url)

        return httpx.Response(
            status_code=200,
            json={"choices": [{"message": {"content": "Resposta gerada com raciocínio"}}]},
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    client = OpenAIGenerativeClient(
        api_key="test-key",
        model="o3-mini",
        reasoning_effort="high",
    )

    response = await client.generate_text("Analise este curso")

    assert response == "Resposta gerada com raciocínio"

    assert captured_payload["model"] == "o3-mini"

    assert captured_payload["reasoning_effort"] == "high"

    assert "temperature" not in captured_payload
