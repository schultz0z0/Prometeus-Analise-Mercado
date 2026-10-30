"""Validação segura das dependências reais exigidas pelo workflow de análise."""

from __future__ import annotations

from dataclasses import dataclass, field

from prometeus.domain.configuration import AppSettings

ACTOR_SETTING_BY_SOURCE: dict[str, str] = {
    "google_search": "APIFY_ACTOR_GOOGLE_SEARCH",
    "web_crawler": "APIFY_ACTOR_WEB_CRAWLER",
    "meta_ads_library": "APIFY_ACTOR_META_AD_LIBRARY",
    "linkedin": "APIFY_ACTOR_LINKEDIN",
    "linkedin_jobs": "APIFY_ACTOR_LINKEDIN_JOBS",
    "instagram": "APIFY_ACTOR_INSTAGRAM",
    "tiktok": "APIFY_ACTOR_TIKTOK",
    "youtube_comments": "APIFY_ACTOR_YOUTUBE_COMMENTS",
    "reddit": "APIFY_ACTOR_REDDIT",
    "google_trends": "APIFY_ACTOR_GOOGLE_TRENDS",
    "google_analytics": "APIFY_ACTOR_GOOGLE_ANALYTICS",
}


@dataclass(frozen=True)
class PreflightIssue:
    code: str
    message: str
    source: str | None = None


@dataclass(frozen=True)
class RuntimePreflightReport:
    ready: bool
    ai_mode: str
    jev_enabled: bool
    required_sources: list[str]
    synthetic_sources: list[str]
    errors: list[PreflightIssue] = field(default_factory=list)
    warnings: list[PreflightIssue] = field(default_factory=list)


def _effective_ai_mode(settings: AppSettings, errors: list[PreflightIssue]) -> str:
    requested = settings.AI_MODE.strip().lower()
    if requested not in {"auto", "traditional", "hybrid", "shadow"}:
        errors.append(
            PreflightIssue(
                code="ai_mode_invalid",
                message="AI_MODE deve ser auto, traditional, hybrid ou shadow.",
            )
        )
        return requested

    if requested == "auto":
        return "hybrid" if settings.is_jev_configured else "traditional"
    return requested


def validate_runtime_preflight(settings: AppSettings) -> RuntimePreflightReport:
    """Valida configuração sem incluir tokens, chaves ou valores secretos nos erros."""
    errors: list[PreflightIssue] = []
    warnings: list[PreflightIssue] = []
    ai_mode = _effective_ai_mode(settings, errors)

    if not settings.is_traditional_llm_configured:
        errors.append(
            PreflightIssue(
                code="llm_credentials_missing",
                message="A LLM tradicional selecionada não possui credencial configurada.",
            )
        )

    if ai_mode == "hybrid" and not settings.is_jev_configured:
        errors.append(
            PreflightIssue(
                code="jev_credentials_missing",
                message="O modo híbrido exige uma credencial TypeSafe/JEV configurada.",
            )
        )

    required_sources = settings.required_market_sources
    if required_sources and not settings.APIFY_TOKEN.strip():
        errors.append(
            PreflightIssue(
                code="apify_credentials_missing",
                message="As fontes externas obrigatórias exigem um token Apify configurado.",
            )
        )

    for source in required_sources:
        setting_name = ACTOR_SETTING_BY_SOURCE.get(source)
        if setting_name is None:
            errors.append(
                PreflightIssue(
                    code="source_unknown",
                    source=source,
                    message=f"A fonte obrigatória '{source}' não existe no registry permitido.",
                )
            )
            continue
        if not str(getattr(settings, setting_name, "")).strip():
            errors.append(
                PreflightIssue(
                    code="actor_missing",
                    source=source,
                    message=f"A fonte obrigatória '{source}' não possui Actor configurado.",
                )
            )

    synthetic_sources = (
        ["institutional_history"] if settings.ALLOW_SYNTHETIC_INSTITUTIONAL_HISTORY else []
    )

    return RuntimePreflightReport(
        ready=not errors,
        ai_mode=ai_mode,
        jev_enabled=ai_mode == "hybrid",
        required_sources=required_sources,
        synthetic_sources=synthetic_sources,
        errors=errors,
        warnings=warnings,
    )
