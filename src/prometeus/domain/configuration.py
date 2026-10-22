"""Módulo de configuração e governança multi-tenant do Prometeus.

Valida parâmetros de ambiente, pesos de scoring, pilares obrigatórios
e restrições operacionais críticas (ex.: proibição de jev-latest em produção).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from prometeus.domain.analyses import DomainError


class ConfigurationError(DomainError):
    """Exceção levantada quando configurações de tenant, scoring ou env são inválidas."""

    pass


class TenantInstitution(BaseModel):
    id: str
    display_name: str
    locale: str = "pt-BR"
    timezone: str = "America/Sao_Paulo"
    currency: str = "BRL"


class TenantBranding(BaseModel):
    product_name: str = "Prometeus"
    product_descriptor: str = "Inteligência para Produtos Educacionais"
    product_vendor: str = "Agência Prometeus"


class TenantFeatures(BaseModel):
    paid_competition: bool = True
    social_listening: bool = True
    job_market: bool = True
    pricing: bool = True


class TenantAdapters(BaseModel):
    institutional: str = "ens"


class TenantProfiles(BaseModel):
    scoring: str = "default-v1"
    retention: str = "ens-pending-approval"


class TenantWebhooks(BaseModel):
    events: list[str] = Field(default_factory=list)


class TenantConfig(BaseModel):
    """Configuração white-label e institucional por tenant."""

    schema_version: int = 1
    institution: TenantInstitution
    branding: TenantBranding = Field(default_factory=TenantBranding)
    features: TenantFeatures = Field(default_factory=TenantFeatures)
    adapters: TenantAdapters = Field(default_factory=TenantAdapters)
    profiles: TenantProfiles = Field(default_factory=TenantProfiles)
    webhooks: TenantWebhooks = Field(default_factory=TenantWebhooks)


class ScoringGates(BaseModel):
    minimum_coverage: float = 0.80
    minimum_confidence: float = 0.75


class ScoringThresholds(BaseModel):
    approved: float = 75.0
    approved_with_adjustments: float = 60.0
    boundary_review_margin: float = 3.0


class ScoringProfileConfig(BaseModel):
    """Perfil de pesos e limiares do motor determinístico de viabilidade."""

    schema_version: int = 1
    profile_id: str
    status: str = "hypothesis"
    weights: dict[str, float]
    gates: ScoringGates = Field(default_factory=ScoringGates)
    thresholds: ScoringThresholds = Field(default_factory=ScoringThresholds)
    required_pillars: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_weights_and_pillars(self) -> ScoringProfileConfig:
        # Validação 1: Soma dos pesos deve ser exatamente 1.0
        total_weight = sum(self.weights.values())
        if not math.isclose(total_weight, 1.0, abs_tol=1e-5):
            raise ConfigurationError(
                f"A soma dos pesos deve somar 1.0. Soma atual: {total_weight:.4f}"
            )

        # Validação 2: Todos os pesos devem ser não-negativos
        for pillar, weight in self.weights.items():
            if weight < 0:
                raise ConfigurationError(
                    f"Peso do pilar '{pillar}' não pode ser negativo: {weight}"
                )

        # Validação 3: Pilares obrigatórios devem existir no dicionário de pesos
        for required in self.required_pillars:
            if required not in self.weights:
                raise ConfigurationError(
                    f"Pilar obrigatório '{required}' não está presente na definição de pesos: {list(self.weights.keys())}"
                )

        return self


class AppSettings(BaseSettings):
    """Configurações globais carregadas de variáveis de ambiente e .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_NAME: str = "prometeus"
    APP_VERSION: str = "0.1.0"
    PRODUCT_NAME: str = "Prometeus"
    PRODUCT_DESCRIPTOR: str = "Inteligência para Produtos Educacionais"
    PRODUCT_VENDOR_NAME: str = "Agência Prometeus"
    LOG_LEVEL: str = "INFO"
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    DATABASE_URL: str = "postgresql+asyncpg://prometeus:prometeus@localhost:5432/prometeus"
    REDIS_URL: str = "redis://localhost:6379/0"
    EVIDENCE_STORAGE_PATH: str = "var/evidence"

    JEV_MODEL: str = "jev-latest"
    JEV_TIMEOUT_SECONDS: int = 15
    JEV_MAX_RETRIES: int = 2
    JEV_REVIEW_CONFIDENCE_THRESHOLD: float = 0.75
    TYPESAFE_API_KEY: str = ""
    JEV_BASE_URL: str = "https://api.typesafe.ai/v1"

    INSTITUTION_ID: str = "ens"
    INSTITUTION_CONFIG_PATH: str = "config/tenants/ens.example.yaml"
    SCORING_PROFILE_PATH: str = "config/scoring/default-v1.example.yaml"

    SERVICE_API_KEYS: str = ""
    SHADOW_MODE: bool = False
    KILL_SWITCH_ACTIVE: bool = False


def validate_environment_and_models(settings: AppSettings) -> None:
    """Valida invariantes críticas de deployment e governança de IA."""
    env = settings.APP_ENV.strip().lower()
    jev_model = settings.JEV_MODEL.strip().lower()

    if env == "production" and jev_model == "jev-latest":
        raise ConfigurationError(
            "O uso de 'jev-latest' é expressamente proibido em ambiente de produção (ADR-0003). "
            "Fixe uma versão imutável aprovada no gate (ex.: 'jev-v1.2.0')."
        )


def load_tenant_config(path: Path | str) -> TenantConfig:
    """Carrega e valida o arquivo YAML de configuração do tenant."""
    file_path = Path(path)
    if not file_path.exists():
        raise ConfigurationError(f"Arquivo de configuração de tenant não encontrado: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)

    try:
        return TenantConfig.model_validate(data)
    except Exception as exc:
        raise ConfigurationError(
            f"Erro ao validar configuração do tenant em {file_path}: {exc}"
        ) from exc


def load_scoring_profile(path: Path | str) -> ScoringProfileConfig:
    """Carrega e valida o arquivo YAML de perfil de pontuação."""
    file_path = Path(path)
    if not file_path.exists():
        raise ConfigurationError(f"Arquivo de perfil de scoring não encontrado: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)

    try:
        return ScoringProfileConfig.model_validate(data)
    except Exception as exc:
        raise ConfigurationError(
            f"Erro ao validar perfil de scoring em {file_path}: {exc}"
        ) from exc
