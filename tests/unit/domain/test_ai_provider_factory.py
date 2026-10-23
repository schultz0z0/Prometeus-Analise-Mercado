import pytest

from prometeus.domain.configuration import AppSettings, ConfigurationError
from prometeus.infrastructure.factory import get_decision_model, get_generative_model
from prometeus.infrastructure.jev.client import TypeSafeJEVClient
from prometeus.infrastructure.llm.decision_adapter import LLMDecisionAdapter


def settings(**overrides: object) -> AppSettings:
    values: dict[str, object] = {
        "AI_MODE": "traditional",
        "GEN_LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-real-test",
        "TYPESAFE_API_KEY": "",
    }
    values.update(overrides)
    return AppSettings(_env_file=None, **values)


def test_traditional_mode_uses_real_llm_decision_adapter_even_if_jev_key_exists() -> None:
    model = get_decision_model(
        settings(AI_MODE="traditional", TYPESAFE_API_KEY="typesafe-unused")
    )
    assert isinstance(model, LLMDecisionAdapter)


def test_auto_mode_uses_traditional_llm_while_jev_is_disabled() -> None:
    model = get_decision_model(settings(AI_MODE="auto", TYPESAFE_API_KEY=""))
    assert isinstance(model, LLMDecisionAdapter)


def test_hybrid_mode_uses_jev_only_when_both_models_are_configured() -> None:
    model = get_decision_model(
        settings(AI_MODE="hybrid", TYPESAFE_API_KEY="typesafe-real-test")
    )
    assert isinstance(model, TypeSafeJEVClient)


def test_factory_refuses_unconfigured_traditional_llm() -> None:
    with pytest.raises(ConfigurationError, match="LLM tradicional"):
        get_generative_model(
            settings(OPENAI_API_KEY="", CHATGPT_ACCESS_TOKEN="")
        )


def test_factory_refuses_hybrid_mode_without_jev_credentials() -> None:
    with pytest.raises(ConfigurationError, match="modo híbrido"):
        get_decision_model(settings(AI_MODE="hybrid", TYPESAFE_API_KEY=""))


def test_factory_refuses_unknown_ai_mode() -> None:
    with pytest.raises(ConfigurationError, match="AI_MODE"):
        get_decision_model(settings(AI_MODE="synthetic"))

