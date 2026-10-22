from pathlib import Path

import pytest

from prometeus.domain.configuration import (
    AppSettings,
    ConfigurationError,
    ScoringProfileConfig,
    load_scoring_profile,
    load_tenant_config,
    validate_environment_and_models,
)


def test_load_tenant_config_from_yaml() -> None:
    tenant_file = Path("config/tenants/ens.example.yaml")
    config = load_tenant_config(tenant_file)
    assert config.institution.id == "ens"
    assert config.institution.display_name == "Escola de Negócios e Seguros"
    assert config.branding.product_name == "Prometeus"
    assert config.branding.product_vendor == "Agência Prometeus"
    assert config.features.pricing is True


def test_load_scoring_profile_valid() -> None:
    scoring_file = Path("config/scoring/default-v1.example.yaml")
    profile = load_scoring_profile(scoring_file)
    assert profile.profile_id == "default-v1"
    assert len(profile.weights) == 6
    assert abs(sum(profile.weights.values()) - 1.0) < 1e-6
    assert "internal_history" in profile.required_pillars
    assert "search_and_media" in profile.required_pillars


def test_scoring_weights_must_sum_to_one() -> None:
    # Invalid weights sum (0.80)
    invalid_data = {
        "schema_version": 1,
        "profile_id": "invalid-sum",
        "status": "hypothesis",
        "weights": {
            "internal_history": 0.40,
            "search_and_media": 0.40,
        },
        "gates": {"minimum_coverage": 0.8, "minimum_confidence": 0.75},
        "thresholds": {
            "approved": 75,
            "approved_with_adjustments": 60,
            "boundary_review_margin": 3,
        },
        "required_pillars": ["internal_history"],
    }
    with pytest.raises(ConfigurationError, match="pesos deve somar 1.0"):
        ScoringProfileConfig.model_validate(invalid_data)


def test_required_pillars_must_exist_in_weights() -> None:
    invalid_data = {
        "schema_version": 1,
        "profile_id": "missing-pillar",
        "status": "hypothesis",
        "weights": {
            "internal_history": 0.50,
            "search_and_media": 0.50,
        },
        "gates": {"minimum_coverage": 0.8, "minimum_confidence": 0.75},
        "thresholds": {
            "approved": 75,
            "approved_with_adjustments": 60,
            "boundary_review_margin": 3,
        },
        "required_pillars": ["non_existent_pillar"],
    }
    with pytest.raises(ConfigurationError, match="Pilar obrigatório .* não está presente"):
        ScoringProfileConfig.model_validate(invalid_data)


def test_jev_latest_prohibited_in_production() -> None:
    # In production, jev-latest must be rejected
    settings = AppSettings(
        APP_ENV="production",
        JEV_MODEL="jev-latest",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/prometeus",
    )
    with pytest.raises(ConfigurationError, match="expressamente proibido em ambiente de produção"):
        validate_environment_and_models(settings)


def test_jev_latest_allowed_in_development() -> None:
    # In development, jev-latest is allowed
    settings = AppSettings(
        APP_ENV="development",
        JEV_MODEL="jev-latest",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/prometeus",
    )
    # Should not raise
    validate_environment_and_models(settings)


def test_pinned_model_allowed_in_production() -> None:
    # In production, pinned model like jev-v1.2.0 is allowed
    settings = AppSettings(
        APP_ENV="production",
        JEV_MODEL="jev-2026.1",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/prometeus",
    )
    validate_environment_and_models(settings)
