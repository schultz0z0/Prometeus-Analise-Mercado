"""Vocabulário público; chaves técnicas ficam nos contratos de auditoria."""

PILLAR_LABELS = {
    "internal_history": "Histórico institucional",
    "paid_competition": "Concorrência em mídia paga",
    "search_and_media": "Interesse de busca e tendência",
    "employability": "Empregabilidade e vagas",
    "syllabus_fit": "Aderência curricular",
    "pricing": "Precificação",
}
SOURCE_LABELS = {
    "google_search": "Google e sites",
    "web_crawler": "Sites de ofertas",
    "meta_ads_library": "Meta Ads",
    "linkedin": "LinkedIn empresas",
    "linkedin_jobs": "LinkedIn vagas",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "youtube_comments": "YouTube",
    "google_trends": "Google Trends",
    "reddit": "Reddit",
}


def public_missing_reason(reason: str) -> str:
    if "feature" in reason.casefold():
        return "Não foram obtidos dados verificados suficientes para esta dimensão."
    if reason == "Preço proposto sem valor ou proveniência verificável":
        return "O preço proposto precisa de valor e periodicidade explicitamente informados."
    return reason
