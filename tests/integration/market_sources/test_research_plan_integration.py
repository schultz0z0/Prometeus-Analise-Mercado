"""Testes de integração para ResearchPlanService (Etapa 05)."""

from prometeus.application.research_plan import ResearchPlanService
from prometeus.domain.configuration import (
    TenantAdapters,
    TenantBranding,
    TenantConfig,
    TenantFeatures,
    TenantInstitution,
    TenantProfiles,
)
from prometeus.domain.ports.market_sources import (
    KeywordSet,
    ResearchPlanStatus,
)


def create_sample_tenant_config(features: TenantFeatures) -> TenantConfig:
    return TenantConfig(
        schema_version=1,
        institution=TenantInstitution(id="ens", display_name="Escola de Negócios e Seguros"),
        branding=TenantBranding(),
        features=features,
        adapters=TenantAdapters(),
        profiles=TenantProfiles(),
    )


def test_research_plan_respects_tenant_features() -> None:
    service = ResearchPlanService()
    kw_set = KeywordSet(
        primary_keywords=["seguro cyber", "subscricao riscos"],
        secondary_keywords=["cyber insurance"],
    )

    # 1. Tenant completo com todas as features
    full_config = create_sample_tenant_config(
        TenantFeatures(paid_competition=True, social_listening=True, job_market=True)
    )
    plan_full = service.generate_plan(
        analysis_id="an-full",
        tenant_config=full_config,
        keyword_set=kw_set,
        budget_limit_usd=3.00,
    )

    assert "google_trends" in plan_full.enabled_sources
    assert "google_ads" in plan_full.enabled_sources
    assert "youtube" in plan_full.enabled_sources
    assert "apify_linkedin_jobs" in plan_full.enabled_sources
    assert "apify_social_listening" in plan_full.enabled_sources
    assert plan_full.budget_limit_usd == 3.00

    # 2. Tenant restrito (sem social listening e sem job market)
    restricted_config = create_sample_tenant_config(
        TenantFeatures(paid_competition=True, social_listening=False, job_market=False)
    )
    plan_restricted = service.generate_plan(
        analysis_id="an-restr",
        tenant_config=restricted_config,
        keyword_set=kw_set,
    )

    assert "youtube" not in plan_restricted.enabled_sources
    assert "apify_social_listening" not in plan_restricted.enabled_sources
    assert "apify_linkedin_jobs" not in plan_restricted.enabled_sources
    assert "google_trends" in plan_restricted.enabled_sources


def test_research_plan_cache_key_is_deterministic() -> None:
    service = ResearchPlanService()
    tenant = create_sample_tenant_config(TenantFeatures())
    kw1 = KeywordSet(primary_keywords=["a", "b"], secondary_keywords=["c"])
    kw2 = KeywordSet(primary_keywords=["b", "a"], secondary_keywords=["c"])  # Ordem trocada

    plan1 = service.generate_plan("an-1", tenant, kw1)
    plan2 = service.generate_plan("an-2", tenant, kw2)

    assert plan1.cache_key == plan2.cache_key


def test_research_plan_budget_exceeded_transition() -> None:
    service = ResearchPlanService()
    tenant = create_sample_tenant_config(TenantFeatures())
    kw = KeywordSet(primary_keywords=["termo"])
    plan = service.generate_plan("an-1", tenant, kw, budget_limit_usd=0.50)

    assert plan.status == ResearchPlanStatus.PLANNED
    assert plan.has_budget_for(0.40) is True

    plan.record_cost(0.40)
    assert plan.spent_usd == 0.40
    assert plan.status == ResearchPlanStatus.PLANNED
    assert plan.has_budget_for(0.20) is False

    plan.record_cost(0.20)  # Total 0.60 > 0.50
    assert plan.status == ResearchPlanStatus.EXCEEDED_BUDGET
