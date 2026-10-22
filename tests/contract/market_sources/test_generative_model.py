"""Testes de contrato para modelos generativos (FakeGenerativeModel e OpenAIGenerativeClient)."""

from pathlib import Path

import httpx
import pytest

from prometeus.infrastructure.llm.client import (
    GenerativeModelError,
    OpenAIGenerativeClient,
)
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


@pytest.mark.asyncio
async def test_fake_generative_model_canned() -> None:
    model = FakeGenerativeModel(canned_keywords=["termo 1", "termo 2", "termo 3"])
    candidates = await model.generate_keyword_candidates(
        course_title="MBA em Riscos",
        description="Curso avançado",
        target_audience="Executivos",
        max_candidates=2,
    )
    assert candidates == ["termo 1", "termo 2"]
    assert len(model.call_history) == 1


@pytest.mark.asyncio
async def test_fake_generative_model_deterministic_fallback() -> None:
    model = FakeGenerativeModel()
    candidates = await model.generate_keyword_candidates(
        course_title="Subscrição de Riscos",
        description="Análise",
        target_audience="Subscritores",
        max_candidates=4,
    )
    assert len(candidates) == 4
    assert "curso subscrição de riscos" in candidates


@pytest.mark.asyncio
async def test_openai_generative_client_keyword_candidates(tmp_path: Path) -> None:
    # Cria prompt YAML temporário
    prompt_yaml = tmp_path / "keyword-candidates-v1.yaml"
    prompt_yaml.write_text(
        "system_prompt: 'Retorne JSON'\nuser_template: 'Curso: {course_title}'\n",
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers.get("Authorization") == "Bearer test-openai-key"

        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '```json\n["mba subscricao", "curso riscos corporativos", "pos graduacao ens"]\n```'
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenAIGenerativeClient(
            api_key="test-openai-key",
            http_client=http_client,
            prompts_dir=tmp_path,
        )
        candidates = await client.generate_keyword_candidates(
            course_title="MBA em Subscrição",
            description="Descrição",
            target_audience="Público",
            max_candidates=10,
        )

    assert len(candidates) == 3
    assert "mba subscricao" in candidates
    assert "curso riscos corporativos" in candidates


@pytest.mark.asyncio
async def test_openai_generative_client_handles_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenAIGenerativeClient(http_client=http_client)

        with pytest.raises(GenerativeModelError, match="Falha de execução do modelo generativo"):
            await client.generate_text("Teste prompt")
