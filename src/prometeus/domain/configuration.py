"""Módulo de configuração e governança multi-tenant do Prometeus.

Valida parâmetros de ambiente, pesos de scoring, pilares obrigatórios
e restrições operacionais críticas (ex.: proibição de jev-latest em produção).
"""

from __future__ import annotations

import base64
import ipaddress
import json
import math
import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from prometeus.domain.analyses import DomainError


class ConfigurationError(DomainError):
    """Exceção levantada quando configurações de tenant, scoring ou env são inválidas."""

    pass


class TenantNotFoundError(ConfigurationError):
    """Exceção levantada quando o arquivo de configuração de um tenant solicitado não existe."""

    pass


class TenantInstitution(BaseModel):
    id: str
    display_name: str
    domains: list[str] = Field(default_factory=list)
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
    target_url: str | None = None


def _normalize_domain(raw: str) -> str:
    candidate = str(raw or "").strip().lower()
    if "://" in candidate:
        parsed = urlsplit(candidate)
        candidate = (parsed.hostname or "").strip().lower()
    else:
        candidate = candidate.split("/", 1)[0].strip().lower()
    candidate = candidate.removeprefix("www.")
    if not candidate or "." not in candidate or any(ch.isspace() for ch in candidate):
        raise ConfigurationError(f"Domínio inválido na configuração do tenant: {raw!r}")
    return candidate


def _validate_https_url(url: str | None) -> str | None:
    if url is None:
        return None
    cleaned = str(url).strip()
    if not cleaned:
        return None
    parsed = urlsplit(cleaned)
    host = (parsed.hostname or "").strip().lower()
    if parsed.scheme != "https" or not host or "." not in host:
        raise ConfigurationError(f"URL institucional/social exige HTTPS válido: {url!r}")
    if host in {"localhost"}:
        raise ConfigurationError(f"Host local proibido na configuração do ecossistema: {url!r}")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ConfigurationError(f"IP privado proibido na configuração do ecossistema: {url!r}")
    except ValueError:
        pass
    return cleaned


class SocialChannelsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instagram_handle: str | None = None
    instagram_url: str | None = None
    linkedin_url: str | None = None
    linkedin_company: str | None = None
    linkedin_scope: Literal["national", "global", "unconfirmed"] = "national"
    youtube_url: str | None = None
    facebook_url: str | None = None

    @model_validator(mode="after")
    def validate_channels(self) -> SocialChannelsConfig:
        object.__setattr__(self, "instagram_url", _validate_https_url(self.instagram_url))
        object.__setattr__(self, "linkedin_url", _validate_https_url(self.linkedin_url))
        object.__setattr__(self, "youtube_url", _validate_https_url(self.youtube_url))
        object.__setattr__(self, "facebook_url", _validate_https_url(self.facebook_url))
        if self.instagram_handle is not None:
            handle = self.instagram_handle.strip().lstrip("@").lower()
            object.__setattr__(self, "instagram_handle", handle or None)
        return self


class CompetitorProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    category: Literal[
        "direct_specialist",
        "executive_business",
        "technical_academic",
        "scale_ead",
        "legal_niche",
        "tech_edtech",
    ]
    domains: list[str]
    portal_url: str | None = None
    social: SocialChannelsConfig = Field(default_factory=SocialChannelsConfig)
    focus_notes: str = ""

    @model_validator(mode="after")
    def validate_competitor(self) -> CompetitorProfileConfig:
        if not self.domains:
            raise ConfigurationError(f"Concorrente '{self.id}' exige ao menos um domínio.")
        normalized = list(dict.fromkeys(_normalize_domain(d) for d in self.domains))
        object.__setattr__(self, "domains", normalized)
        object.__setattr__(self, "portal_url", _validate_https_url(self.portal_url))
        return self


class SectorRadarActorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    priority: Literal["primary", "secondary"] = "primary"
    domains: list[str]
    social: SocialChannelsConfig = Field(default_factory=SocialChannelsConfig)
    monitoring_focus: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_sector_actor(self) -> SectorRadarActorConfig:
        if not self.domains:
            raise ConfigurationError(f"Ator do radar '{self.id}' exige ao menos um domínio.")
        normalized = list(dict.fromkeys(_normalize_domain(d) for d in self.domains))
        object.__setattr__(self, "domains", normalized)
        return self


class TenantEcosystemConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competitors: list[CompetitorProfileConfig] = Field(default_factory=list)
    sector_radar: list[SectorRadarActorConfig] = Field(default_factory=list)
    allow_extra_intake_competitors: bool = True
    radar_ttl_hours: int = Field(default=168, ge=1, le=720)


class TenantConfig(BaseModel):
    """Configuração white-label e institucional por tenant."""

    schema_version: int = 1
    institution: TenantInstitution
    branding: TenantBranding = Field(default_factory=TenantBranding)
    features: TenantFeatures = Field(default_factory=TenantFeatures)
    adapters: TenantAdapters = Field(default_factory=TenantAdapters)
    profiles: TenantProfiles = Field(default_factory=TenantProfiles)
    webhooks: TenantWebhooks = Field(default_factory=TenantWebhooks)
    ecosystem: TenantEcosystemConfig = Field(default_factory=TenantEcosystemConfig)

    @model_validator(mode="after")
    def validate_ecosystem_isolation(self) -> TenantConfig:
        own_domains = {_normalize_domain(d) for d in self.institution.domains if str(d).strip()}
        comp_domains: set[str] = set()
        seen_comp_ids: set[str] = set()
        for comp in self.ecosystem.competitors:
            if comp.id in seen_comp_ids:
                raise ConfigurationError(f"Concorrente duplicado no tenant: '{comp.id}'")
            seen_comp_ids.add(comp.id)
            overlap_own = own_domains & set(comp.domains)
            if overlap_own:
                raise ConfigurationError(
                    f"Concorrente '{comp.id}' compartilha domínio da própria instituição: {sorted(overlap_own)}"
                )
            overlap_comp = comp_domains & set(comp.domains)
            if overlap_comp:
                raise ConfigurationError(
                    f"Concorrente '{comp.id}' duplica domínio já atribuído: {sorted(overlap_comp)}"
                )
            comp_domains.update(comp.domains)

        seen_radar_ids: set[str] = set()
        radar_domains: set[str] = set()
        for actor in self.ecosystem.sector_radar:
            if actor.id in seen_radar_ids:
                raise ConfigurationError(f"Ator do radar duplicado no tenant: '{actor.id}'")
            seen_radar_ids.add(actor.id)
            overlap_own = own_domains & set(actor.domains)
            if overlap_own:
                raise ConfigurationError(
                    f"Ator do radar '{actor.id}' compartilha domínio da própria instituição: {sorted(overlap_own)}"
                )
            overlap_comp = comp_domains & set(actor.domains)
            if overlap_comp:
                raise ConfigurationError(
                    f"Ator do radar '{actor.id}' conflita com domínio de concorrente educacional: {sorted(overlap_comp)}"
                )
            overlap_radar = radar_domains & set(actor.domains)
            if overlap_radar:
                raise ConfigurationError(
                    f"Ator do radar '{actor.id}' duplica domínio já atribuído: {sorted(overlap_radar)}"
                )
            radar_domains.update(actor.domains)
        return self


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
    aggregation_mode: str = "weighted_sum"
    historical_method: str = "legacy"
    weights: dict[str, float]
    gates: ScoringGates = Field(default_factory=ScoringGates)
    thresholds: ScoringThresholds = Field(default_factory=ScoringThresholds)
    required_pillars: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_weights_and_pillars(self) -> ScoringProfileConfig:
        if self.aggregation_mode not in {"weighted_sum", "observed_mean"}:
            raise ConfigurationError("Modo de agregação de scoring inválido.")
        if self.historical_method not in {"legacy", "ipd"}:
            raise ConfigurationError("Método de histórico inválido.")
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

    # JEV / TypeSafe AI (Motor de Decisão System One - Opcional / Modo Híbrido)
    AI_MODE: str = "auto"  # auto, traditional, hybrid, shadow
    JEV_NON_INFERIORITY_THRESHOLD: float = 0.90
    SHADOW_DECISION_MODE: bool = False
    JEV_MODEL: str = "jev-latest"
    JEV_TIMEOUT_SECONDS: int = 15
    JEV_MAX_RETRIES: int = 2
    JEV_REVIEW_CONFIDENCE_THRESHOLD: float = 0.75
    TYPESAFE_API_KEY: str = ""
    JEV_BASE_URL: str = "https://api.typesafe.ai/v1"

    # LLM Tradicional / Generativa (Síntese de Texto, Dossiê, Chatbot e Fallback de Decisões)
    GEN_LLM_PROVIDER: str = "openai"  # adaptadores implementados: openai, openrouter
    GEN_LLM_MODEL: str = "gpt-4o-mini"
    GEN_LLM_REASONING_EFFORT: str = ""  # none, low, medium, high, extra_high, max
    GEN_LLM_TIMEOUT_SECONDS: int = 60
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    CHATGPT_ACCESS_TOKEN: str = ""
    CHATGPT_REFRESH_TOKEN: str = ""
    CHATGPT_ID_TOKEN: str = ""
    CHATGPT_OAUTH_CLIENT_ID: str = ""
    CHATGPT_OAUTH_SCOPES: str = ""
    CHATGPT_TOKEN_EXPIRES_AT: float = 0.0
    CHATGPT_CREDENTIALS_PATH: str = "var/chatgpt/credentials.json"
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Apify / Coleta de Dados Web (Scraping de Concorrentes e Vagas)
    APIFY_TOKEN: str = ""
    APIFY_BASE_URL: str = "https://api.apify.com/v2"
    # Legacy snapshots only; new analyses use collection-v2 without a monetary cap.
    APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS: float | None = None
    APIFY_DISCOVERY_MCP_ENABLED: bool = False
    APIFY_ACTOR_GOOGLE_SEARCH: str = ""
    APIFY_ACTOR_WEB_CRAWLER: str = ""
    APIFY_ACTOR_META_AD_LIBRARY: str = ""
    APIFY_ACTOR_LINKEDIN: str = ""
    APIFY_ACTOR_LINKEDIN_JOBS: str = ""
    APIFY_ACTOR_INSTAGRAM: str = ""
    APIFY_ACTOR_TIKTOK: str = ""
    APIFY_ACTOR_YOUTUBE_COMMENTS: str = ""
    APIFY_ACTOR_REDDIT: str = ""
    APIFY_ACTOR_GOOGLE_TRENDS: str = ""
    APIFY_ACTOR_GOOGLE_ANALYTICS: str = ""
    APIFY_REQUIRED_SOURCES: str = (
        "google_search,web_crawler,meta_ads_library,linkedin,linkedin_jobs,"
        "instagram,tiktok,youtube_comments"
    )
    ALLOW_SYNTHETIC_INSTITUTIONAL_HISTORY: bool = True

    INSTITUTION_ID: str = "ens"
    INSTITUTION_CONFIG_PATH: str = "config/tenants/ens.example.yaml"
    SCORING_PROFILE_PATH: str = "config/scoring/portfolio-v2.yaml"

    SERVICE_API_KEYS: str = ""
    AUTH_ADMIN_KEY_PATH: str = "var/auth/admin.key"
    WEBHOOK_SECRET: str = ""
    WEBHOOK_TARGET_URL: str = ""
    SHADOW_MODE: bool = False
    KILL_SWITCH_ACTIVE: bool = False

    @property
    def is_jev_configured(self) -> bool:
        """Indica se as credenciais do TypeSafe JEV foram fornecidas para habilitar o modo híbrido."""
        return bool(self.TYPESAFE_API_KEY and self.TYPESAFE_API_KEY.strip())

    @property
    def is_traditional_llm_configured(self) -> bool:
        """Indica se o adaptador implementado possui uma API key compatível."""
        provider = self.GEN_LLM_PROVIDER.lower()
        if provider in {"openai", "openrouter"}:
            return bool(self.OPENAI_API_KEY.strip())
        if provider in {"chatgpt_oauth", "codex"}:
            credential_path = Path(self.CHATGPT_CREDENTIALS_PATH)
            if credential_path.is_file():
                try:
                    stored = json.loads(credential_path.read_text(encoding="utf-8"))
                    scopes = stored.get("scopes", [])
                    return bool(
                        stored.get("access_token")
                        and stored.get("refresh_token")
                        and stored.get("client_id")
                        and isinstance(scopes, list)
                        and "chatgpt.tokens.use.direct" in scopes
                    )
                except (OSError, TypeError, ValueError, json.JSONDecodeError):
                    return False
        if provider in {"chatgpt_oauth", "codex"} and self.CHATGPT_ACCESS_TOKEN.strip():
            try:
                payload_segment = self.CHATGPT_ACCESS_TOKEN.split(".")[1]
                payload_segment += "=" * (-len(payload_segment) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_segment))
                scope = str(payload.get("scope", "")).split()
                audience = payload.get("aud", [])
                if isinstance(audience, str):
                    audience = [audience]
                return (
                    "chatgpt.tokens.use.direct" in scope and "https://api.openai.com/v1" in audience
                )
            except (IndexError, ValueError, TypeError, json.JSONDecodeError):
                return False
        return False

    @property
    def required_market_sources(self) -> list[str]:
        """Fontes externas obrigatórias normalizadas e sem duplicatas."""
        seen: set[str] = set()
        sources: list[str] = []
        for raw in self.APIFY_REQUIRED_SOURCES.split(","):
            source = raw.strip().lower()
            if source and source not in seen:
                seen.add(source)
                sources.append(source)
        return sources


def validate_environment_and_models(settings: AppSettings) -> None:
    """Valida invariantes críticas de deployment e governança de IA."""
    env = settings.APP_ENV.strip().lower()
    jev_model = settings.JEV_MODEL.strip().lower()

    jev_enabled = settings.AI_MODE in {"hybrid", "shadow"} or (
        settings.AI_MODE == "auto" and settings.is_jev_configured
    )
    if env == "production" and jev_enabled and jev_model == "jev-latest":
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


_TENANT_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}$")


def resolve_tenant_config_for_id(
    tenant_id: str,
    settings: AppSettings,
    *,
    allow_synthetic_fallback: bool = False,
) -> TenantConfig:
    """Resolve a configuração do tenant solicitado sem vazar dados entre instituições."""
    clean_id = (tenant_id or "").strip()
    if not _TENANT_SLUG_PATTERN.fullmatch(clean_id):
        raise TenantNotFoundError(f"Tenant '{tenant_id}' inválido ou não encontrado.")

    configured_path = Path(settings.INSTITUTION_CONFIG_PATH)
    if configured_path.is_file():
        try:
            configured_cfg = load_tenant_config(configured_path)
            if configured_cfg.institution.id == clean_id:
                return configured_cfg
        except ConfigurationError:
            pass

    candidates: list[Path] = [Path("config/tenants") / f"{clean_id}.yaml"]
    if settings.APP_ENV.strip().lower() != "production":
        candidates.append(Path("config/tenants") / f"{clean_id}.example.yaml")

    for candidate in candidates:
        if candidate.is_file():
            cfg = load_tenant_config(candidate)
            if cfg.institution.id == clean_id:
                return cfg

    if allow_synthetic_fallback:
        return TenantConfig(
            institution=TenantInstitution(id=clean_id, display_name=clean_id, domains=[])
        )
    raise TenantNotFoundError(f"Tenant '{clean_id}' não encontrado.")


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
