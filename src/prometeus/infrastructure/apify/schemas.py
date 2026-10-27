"""Contratos internos para respostas da API Apify e validação de datasets."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ApifyRunMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    dataset_id: str
    status: str
    actor_id: str
    build_number: str
    cost_usd: float = 0.0


class ApifyExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run: ApifyRunMetadata
    items: list[dict[str, Any]]
    total_items: int


RECOGNIZED_DATASET_FIELDS: dict[str, frozenset[str]] = {
    "google_search": frozenset(
        {"title", "url", "link", "searchQuery", "organicResults", "paidResults"}
    ),
    "web_crawler": frozenset({"url", "loadedUrl", "title", "text", "markdown", "crawl"}),
    "meta_ads_library": frozenset(
        {
            "id",
            "ad_id",
            "adArchiveID",
            "adArchiveId",
            "ad_archive_id",
            "pageName",
            "page_name",
            "snapshot",
            "snapshotUrl",
            "url",
        }
    ),
    "linkedin": frozenset(
        {
            "id",
            "linkedinUrl",
            "url",
            "name",
            "companyName",
            "universalName",
            "tagline",
            "description",
            "websiteUrl",
        }
    ),
    "linkedin_jobs": frozenset(
        {
            "id",
            "jobId",
            "job_id",
            "jobUrl",
            "job_url",
            "link",
            "url",
            "title",
            "positionName",
            "companyName",
            "company",
        }
    ),
    "instagram": frozenset(
        {
            "id",
            "url",
            "inputUrl",
            "shortCode",
            "caption",
            "ownerUsername",
            "name",
            "postsCount",
            "topPosts",
            "latestPosts",
        }
    ),
    "tiktok": frozenset(
        {"id", "webVideoUrl", "url", "text", "authorMeta", "videoMeta", "diggCount", "playCount"}
    ),
    "youtube_comments": frozenset(
        {
            "id",
            "cid",
            "commentId",
            "text",
            "comment",
            "videoId",
            "url",
            "pageUrl",
            "author",
            "title",
            "channelName",
            "channelUrl",
            "channelDescription",
            "channelId",
            "error",
            "note",
        }
    ),
    "reddit": frozenset({"id", "url", "title", "body", "communityName", "username", "dataType"}),
    "google_trends": frozenset(
        {
            "searchTerm",
            "keyword",
            "term",
            "interestOverTime",
            "interestOverTime_timelineData",
            "interestBySubregion",
            "relatedQueries",
            "relatedTopics",
            "url",
            "inputUrlOrTerm",
        }
    ),
    "google_analytics": frozenset({"date", "rows", "metricValues", "dimensionValues"}),
}


def validate_dataset_items(capability: str, payload: Any) -> list[dict[str, Any]]:
    """Rejeita respostas incompatíveis em vez de tratá-las como evidência vazia."""
    if not isinstance(payload, list):
        raise ValueError(f"Dataset de '{capability}' não retornou uma lista JSON.")
    if not payload:
        return []

    recognized = RECOGNIZED_DATASET_FIELDS.get(capability, frozenset())
    items: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Item {index} de '{capability}' não é um objeto JSON.")
        if recognized and not recognized.intersection(item):
            raise ValueError(f"Item {index} de '{capability}' não possui campos reconhecidos.")
        items.append(item)
    return items
