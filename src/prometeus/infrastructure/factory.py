"""Fábrica centralizada de provedores de IA (Híbrido JEV + LLM Tradicional ou 100% Tradicional).

Gerencia automaticamente:
- Modo Híbrido: JEV (TypeSafe AI) para decisões atômicas System One + LLM Tradicional para síntese de texto.
- Modo 100% Tradicional: Caso o JEV não esteja conectado, a LLM Tradicional assume automaticamente ambos os papéis.
- Suporte a conexões diretas via ChatGPT OAuth / Codex (Hermes-agent / OpenClaw style) e API keys padrão (OpenAI, Claude, Gemini).
"""

from __future__ import annotations

import logging
from typing import Any

from prometeus.application.decision_service import DecisionService
from prometeus.application.shadow_decision_service import ShadowDecisionService
from prometeus.domain.configuration import AppSettings, ConfigurationError
from prometeus.domain.ports.decision_model import DecisionModelPort
from prometeus.domain.ports.generative_model import GenerativeModelPort
from prometeus.infrastructure.jev.client import TypeSafeJEVClient
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient
from prometeus.infrastructure.llm.client import (
    ChatGPTPlanGenerativeClient,
    OpenAIGenerativeClient,
)
from prometeus.infrastructure.llm.codex_oauth import ChatGPTCredentialStore
from prometeus.infrastructure.llm.decision_adapter import LLMDecisionAdapter

logger = logging.getLogger(__name__)


def get_generative_model(settings: AppSettings | None = None) -> GenerativeModelPort:
    """Retorna o cliente de LLM Tradicional para síntese de texto, dossiê e chatbot."""
    settings = settings or AppSettings()
    provider = settings.GEN_LLM_PROVIDER.strip().lower()

    if not settings.is_traditional_llm_configured:
        raise ConfigurationError(
            f"A LLM tradicional '{provider or 'não definida'}' não possui credencial configurada."
        )

    if provider in {"openai", "openrouter"}:
        base_url = settings.OPENAI_BASE_URL
        model = settings.GEN_LLM_MODEL or "gpt-4o-mini"
        return OpenAIGenerativeClient(
            base_url=base_url,
            api_key=settings.OPENAI_API_KEY,
            model=model,
            reasoning_effort=settings.GEN_LLM_REASONING_EFFORT,
            timeout_seconds=float(settings.GEN_LLM_TIMEOUT_SECONDS),
        )

    if provider in {"chatgpt_oauth", "codex"}:
        credential_store = ChatGPTCredentialStore(settings.CHATGPT_CREDENTIALS_PATH)
        credentials = credential_store.load()
        return ChatGPTPlanGenerativeClient(
            access_token=(
                credentials.access_token if credentials else settings.CHATGPT_ACCESS_TOKEN
            ),
            base_url=settings.OPENAI_BASE_URL,
            model=(
                credentials.selected_model
                if credentials
                else settings.GEN_LLM_MODEL or "gpt-6.1-sol"
            ),
            reasoning_effort=settings.GEN_LLM_REASONING_EFFORT,
            timeout_seconds=float(settings.GEN_LLM_TIMEOUT_SECONDS),
            credential_store=credential_store if credentials else None,
        )

    raise ConfigurationError(
        f"GEN_LLM_PROVIDER '{provider}' ainda não possui adaptador de runtime implementado."
    )


def get_decision_model(settings: AppSettings | None = None) -> DecisionModelPort:
    """Retorna o motor de decisão System One.

    AI_MODE=traditional sempre usa LLMDecisionAdapter, inclusive com chave JEV.
    Somente AI_MODE=auto escolhe o modo pela presença de credencial JEV;
    hybrid exige essa credencial. Nenhum modo delega cálculos ao modelo.
    """
    settings = settings or AppSettings()
    mode = settings.AI_MODE.strip().lower()

    if mode not in {"auto", "traditional", "hybrid", "shadow"}:
        raise ConfigurationError("AI_MODE deve ser auto, traditional, hybrid ou shadow.")

    if mode in {"traditional", "shadow"}:
        return LLMDecisionAdapter(generative_model=get_generative_model(settings))

    if mode == "hybrid" and not settings.is_jev_configured:
        raise ConfigurationError("O modo híbrido exige TYPESAFE_API_KEY configurada.")

    if mode == "hybrid" or settings.is_jev_configured:
        logger.info(
            f"Modo Híbrido Ativo: Conectado ao TypeSafe JEV (Model: {settings.JEV_MODEL}) para System One."
        )
        return TypeSafeJEVClient(
            base_url=settings.JEV_BASE_URL,
            api_key=settings.TYPESAFE_API_KEY,
            model=settings.JEV_MODEL,
            timeout_seconds=float(settings.JEV_TIMEOUT_SECONDS),
            max_retries=settings.JEV_MAX_RETRIES,
        )

    logger.info(
        "JEV não conectado: Chaveando automaticamente para Modo 100% Tradicional (LLMDecisionAdapter)."
    )
    gen_model = get_generative_model(settings)
    return LLMDecisionAdapter(generative_model=gen_model)


def get_shadow_decision_service(
    settings: AppSettings | None = None,
    session: Any = None,
    packs_dir: str | None = None,
) -> ShadowDecisionService:
    """Retorna o serviço de decisão em Shadow Mode (Fase 6).

    O serviço orquestra a execução primária com a LLM tradicional e a execução
    secundária com o JEV em paralelo, capturando métricas de divergência sem risco
    à execução principal.
    """
    settings = settings or AppSettings()
    gen_model = get_generative_model(settings)
    primary_model = LLMDecisionAdapter(generative_model=gen_model)

    kwargs: dict[str, Any] = {"decision_model": primary_model, "session": session}
    if packs_dir is not None:
        kwargs["packs_dir"] = packs_dir
    primary_service = DecisionService(**kwargs)

    shadow_model: DecisionModelPort
    if settings.is_jev_configured:
        shadow_model = TypeSafeJEVClient(
            base_url=settings.JEV_BASE_URL,
            api_key=settings.TYPESAFE_API_KEY,
            model=settings.JEV_MODEL,
            timeout_seconds=float(settings.JEV_TIMEOUT_SECONDS),
            max_retries=settings.JEV_MAX_RETRIES,
        )
    else:
        shadow_model = FakeDecisionClient(model=settings.JEV_MODEL)

    return ShadowDecisionService(
        primary_service=primary_service,
        shadow_model=shadow_model,
        enabled=True,
    )
