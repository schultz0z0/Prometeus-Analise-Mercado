"""Execução persistente do plano de pesquisa, sem qualquer fallback sintético."""

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.application.sanitization import EvidenceSanitizer
from prometeus.application.tool_capabilities import CAPABILITY_LIMIT_UNITS
from prometeus.domain.market_entities import extract_canonical_entity_id
from prometeus.domain.ports.market_sources import MarketEvidence
from prometeus.domain.research import CourseResearchPlan, PlannedToolCall
from prometeus.infrastructure.apify.client import (
    ApifyActorFailedError,
    ApifyBudgetExceededError,
    ApifyError,
    ApifySchemaDriftError,
    ApifyTimeoutError,
)
from prometeus.infrastructure.apify.registry import ActorConfigurationError, ApifyActorRegistry
from prometeus.infrastructure.apify.schemas import ApifyExecutionResult
from prometeus.infrastructure.db.models import (
    MarketEvidenceModel,
    ResearchPlanModel,
    ToolRunModel,
)


class RequiredSourceBlockedError(RuntimeError):
    """Uma fonte obrigatória falhou ou não produziu evidência válida."""

    def __init__(self, call_id: str, reason: str) -> None:
        self.call_id = call_id
        self.reason = reason
        super().__init__(f"Fonte obrigatória bloqueada em '{call_id}': {reason}")


class ResearchToolExecutor(Protocol):
    async def execute(
        self, call: PlannedToolCall, *, max_total_charge_usd: float
    ) -> ApifyExecutionResult: ...


@dataclass(frozen=True)
class CollectionOutcome:
    research_plan_id: str
    completed_call_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    blocking_failures: list[str] = field(default_factory=list)
    optional_failures: list[str] = field(default_factory=list)
    spent_usd: float = 0.0


class CollectMarketEvidenceService:
    """Executa calls autorizadas e faz checkpoint de runs/evidências no banco."""

    def __init__(
        self,
        session: AsyncSession,
        executor: ResearchToolExecutor,
        registry: ApifyActorRegistry,
        sanitizer: EvidenceSanitizer | None = None,
    ) -> None:
        self.session = session
        self.executor = executor
        self.registry = registry
        self.sanitizer = sanitizer or EvidenceSanitizer()

    async def _ensure_plan(
        self,
        *,
        tenant_id: str,
        plan: CourseResearchPlan,
        understanding_snapshot: dict[str, object] | None,
    ) -> ResearchPlanModel:
        model = await self.session.get(ResearchPlanModel, plan.id)
        if model is None:
            model = ResearchPlanModel(
                id=plan.id,
                analysis_id=plan.analysis_id,
                tenant_id=tenant_id,
                cache_key=plan.snapshot_hash,
                enabled_sources=sorted({call.capability for call in plan.tool_calls}),
                budget_limit_usd=plan.budget_limit_usd,
                spent_usd=0.0,
                allocated_budget={},
                understanding_snapshot=understanding_snapshot or {},
                plan_snapshot=plan.model_dump(mode="json"),
                snapshot_hash=plan.snapshot_hash,
                skill_snapshots=plan.skill_snapshots,
                status="IN_PROGRESS",
            )
            self.session.add(model)
            await self.session.commit()
        return model

    async def _find_run(self, plan_id: str, call_id: str) -> ToolRunModel | None:
        return (
            await self.session.execute(
                select(ToolRunModel).where(
                    ToolRunModel.research_plan_id == plan_id,
                    ToolRunModel.planned_call_id == call_id,
                )
            )
        ).scalar_one_or_none()

    @staticmethod
    def _is_usable_discovered_url(capability: str, value: object) -> bool:
        if not isinstance(value, str) or not value.startswith(("https://", "http://")):
            return False
        if "[" in value or "]" in value or " " in value:
            return False
        try:
            parsed = urlsplit(value)
            if parsed.port not in {None, 80, 443} or parsed.username or parsed.password:
                return False
        except ValueError:
            return False
        hostname = (parsed.hostname or "").lower()
        if (
            not hostname
            or hostname == "api.apify.com"
            or "." not in hostname
            or hostname.endswith((".local", ".localhost", ".internal"))
        ):
            return False
        try:
            if not ipaddress.ip_address(hostname).is_global:
                return False
        except ValueError:
            pass
        if hostname in {
            "www.google.com",
            "google.com",
            "www.google.com.br",
            "google.com.br",
        } and parsed.path.startswith("/search"):
            return False
        if "www." in parsed.path or "http://" in parsed.path or "https://" in parsed.path:
            return False
        if hostname and hostname in parsed.path:
            return False
        if capability == "youtube_comments":
            if hostname in {"youtu.be", "www.youtu.be"}:
                return bool(parsed.path.strip("/")) and "/" not in parsed.path.strip("/")
            return (
                (hostname.endswith(".youtube.com") or hostname == "youtube.com")
                and parsed.path == "/watch"
                and bool(parse_qs(parsed.query).get("v", [""])[0].strip())
            )
        return True

    @staticmethod
    def _canonical_url(value: str) -> str:
        parsed = urlsplit(value)
        query = [
            (key, val)
            for key, val in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in {"gclid", "fbclid", "ref", "trackingid"}
        ]
        hostname = (parsed.hostname or "").lower().removeprefix("www.")
        return urlunsplit(
            ("https", hostname, parsed.path.rstrip("/") or "/", urlencode(sorted(query)), "")
        )

    @staticmethod
    def _dependencies(call: PlannedToolCall) -> list[str]:
        dependencies = call.parameters.get("depends_on", [])
        if isinstance(dependencies, str):
            dependencies = [dependencies]
        if not isinstance(dependencies, list) or any(
            not isinstance(cid, str) for cid in dependencies
        ):
            raise ActorConfigurationError(f"dependências inválidas na chamada '{call.id}'.")
        return list(dict.fromkeys(dependencies))

    @classmethod
    def _ordered_calls(cls, plan: CourseResearchPlan) -> list[PlannedToolCall]:
        """Stable topological order; legacy URL calls depend on discovery calls."""
        by_id = {call.id: call for call in plan.tool_calls}
        search_ids = [call.id for call in plan.tool_calls if call.capability == "google_search"]
        dependencies: dict[str, list[str]] = {}
        for call in plan.tool_calls:
            deps = cls._dependencies(call)
            if not deps and call.capability in {"web_crawler", "youtube_comments"}:
                deps = search_ids
            if any(cid not in by_id or cid == call.id for cid in deps):
                raise ActorConfigurationError(
                    f"dependência desconhecida ou reflexiva em '{call.id}'."
                )
            dependencies[call.id] = deps
        ordered: list[PlannedToolCall] = []
        remaining = list(plan.tool_calls)
        completed: set[str] = set()
        while remaining:
            ready = next(
                (call for call in remaining if set(dependencies[call.id]) <= completed), None
            )
            if ready is None:
                raise ActorConfigurationError("Ciclo no grafo de dependências das ferramentas.")
            ordered.append(ready)
            completed.add(ready.id)
            remaining.remove(ready)
        return ordered

    @staticmethod
    def _extract_payload_urls(payload: object) -> list[object]:
        if not isinstance(payload, dict):
            return []
        found: list[object] = [
            payload.get(key) for key in ("url", "link", "videoUrl", "webVideoUrl")
        ]
        for nested_key in ("organicResults", "paidResults"):
            nested = payload.get(nested_key)
            if isinstance(nested, list):
                for entry in nested:
                    if isinstance(entry, dict):
                        found.extend(entry.get(k) for k in ("url", "link"))
        return found

    async def _resolve_dependent_urls(
        self, call: PlannedToolCall, *, analysis_id: str, research_plan_id: str | None = None
    ) -> PlannedToolCall:
        if call.capability not in {"web_crawler", "youtube_comments"}:
            return call
        dependencies = self._dependencies(call)
        query = (
            select(MarketEvidenceModel)
            .join(ToolRunModel, MarketEvidenceModel.tool_run_id == ToolRunModel.id)
            .where(MarketEvidenceModel.analysis_id == analysis_id)
            .order_by(MarketEvidenceModel.collected_at, MarketEvidenceModel.id)
        )
        if research_plan_id is not None:
            query = query.where(ToolRunModel.research_plan_id == research_plan_id)
        if dependencies:
            query = query.where(ToolRunModel.planned_call_id.in_(dependencies))
        else:
            query = query.where(ToolRunModel.capability == "google_search")
        evidence_rows = (await self.session.execute(query)).scalars().all()
        discovered: list[str] = []
        for evidence in evidence_rows:
            candidates: list[object] = [evidence.source_url]
            for payload in (evidence.raw_payload, evidence.sanitized_data):
                candidates.extend(self._extract_payload_urls(payload))
            for candidate in candidates:
                if (
                    self._is_usable_discovered_url(call.capability, candidate)
                    and candidate not in discovered
                ):
                    discovered.append(str(candidate))
        supplied = call.parameters.get("urls", call.parameters.get("start_urls", []))
        if isinstance(supplied, str):
            supplied = [supplied]
        if isinstance(supplied, list) and supplied:
            authorized = {self._canonical_url(url) for url in discovered}
            discovered = [
                value
                for value in supplied
                if self._is_usable_discovered_url(call.capability, value)
                and self._canonical_url(value) in authorized
            ]
        if call.capability == "web_crawler":
            previous_runs = (
                (
                    await self.session.execute(
                        select(ToolRunModel).where(
                            ToolRunModel.analysis_id == analysis_id,
                            ToolRunModel.capability == "web_crawler",
                            ToolRunModel.status.in_(["SUCCEEDED", "EMPTY"]),
                        )
                    )
                )
                .scalars()
                .all()
            )
            visited = {
                self._canonical_url(url)
                for previous in previous_runs
                for url in previous.parameters.get("resolved_urls", [])
                if isinstance(url, str)
            }
            followed_urls = (
                await self.session.execute(
                    select(MarketEvidenceModel.source_url)
                    .join(ToolRunModel, MarketEvidenceModel.tool_run_id == ToolRunModel.id)
                    .where(
                        MarketEvidenceModel.analysis_id == analysis_id,
                        ToolRunModel.analysis_id == analysis_id,
                        ToolRunModel.capability == "web_crawler",
                        ToolRunModel.status.in_(["SUCCEEDED", "PARTIAL"]),
                    )
                )
            ).scalars()
            visited.update(
                self._canonical_url(url)
                for url in followed_urls
                if self._is_usable_discovered_url("web_crawler", url)
            )
            discovered = [url for url in discovered if self._canonical_url(url) not in visited]
        canonical_seen: set[str] = set()
        unique_urls: list[str] = []
        for url in discovered:
            canonical = self._canonical_url(url)
            if canonical not in canonical_seen:
                canonical_seen.add(canonical)
                unique_urls.append(url)
        if not unique_urls:
            raise ActorConfigurationError(
                f"A capability '{call.capability}' não recebeu URL e nenhuma URL compatível "
                "foi descoberta por uma busca anterior."
            )
        if call.capability == "web_crawler":
            unique_urls = self._prioritize_crawler_urls(
                unique_urls, query=call.query, max_urls=call.max_items
            )
        parameters = dict(call.parameters)
        parameters["urls"] = unique_urls[: call.max_items]
        return call.model_copy(update={"parameters": parameters})

    @classmethod
    def _prioritize_crawler_urls(
        cls,
        urls: list[str],
        query: str = "",
        max_urls: int = 10,
    ) -> list[str]:
        """Rankeamento determinístico de URLs por relevância e diversidade de domínios.

        Prioriza:
        1. Páginas específicas de cursos (mba, pós-graduação, curso, extensão)
        2. URLs contendo termos da consulta
        3. Documentos e PDFs pertinentes
        4. Catálogos e listagens
        5. Diversidade de domínio: no máximo 2 URLs por domínio no lote
        """
        course_terms = {
            "mba",
            "curso",
            "cursos",
            "pos",
            "pos-graduacao",
            "extensao",
            "especializacao",
            "graduacao",
            "treinamento",
        }
        query_tokens = {token.lower() for token in query.split() if len(token) > 2}

        scored_urls: list[tuple[float, str]] = []
        for url in urls:
            if not cls._is_usable_discovered_url("web_crawler", url):
                continue
            parsed = urlsplit(url)
            path_lower = parsed.path.lower()
            score = 0.0

            path_words = set(path_lower.replace("/", " ").replace("-", " ").replace("_", " ").split())
            if any(term in path_words for term in course_terms):
                score += 10.0

            matching_tokens = sum(1 for token in query_tokens if token in path_lower)
            score += matching_tokens * 3.0

            if path_lower.endswith(".pdf"):
                score += 5.0
            elif any(cat in path_lower for cat in ("/catalogo", "/cursos", "/pos-graduacao")):
                score += 2.0
            elif any(article in path_lower for article in ("/noticia", "/noticias", "/artigo", "/blog")):
                score -= 3.0

            scored_urls.append((score, url))

        scored_urls.sort(key=lambda x: x[0], reverse=True)

        domain_counts: dict[str, int] = {}
        prioritized: list[str] = []

        for _, url in scored_urls:
            hostname = (urlsplit(url).hostname or "").lower().removeprefix("www.")
            count = domain_counts.get(hostname, 0)
            if count < 2:
                domain_counts[hostname] = count + 1
                prioritized.append(url)
                if len(prioritized) >= max_urls:
                    break

        return prioritized

    async def _checkpoint_running(
        self,
        *,
        plan: CourseResearchPlan,
        call: PlannedToolCall,
    ) -> ToolRunModel:
        spec = self.registry.require(call.capability)
        model = await self._find_run(plan.id, call.id)
        effective_scope = {
            "capability": call.capability,
            "geography": call.parameters.get("location") or call.parameters.get("country") or call.parameters.get("geo") or "Brasil",
            "time_window": call.parameters.get("time_range") or call.parameters.get("time_window") or call.parameters.get("date_posted"),
            "limit_unit": CAPABILITY_LIMIT_UNITS.get(call.capability, "retained_total"),
            "max_items": call.max_items,
            "query": call.query,
        }
        run_parameters = dict(call.parameters)
        try:
            run_parameters["effective_actor_input"] = self.registry.build_input(call)
        except Exception:
            run_parameters["effective_actor_input"] = None
        run_parameters["effective_scope"] = effective_scope
        if model is None:
            model = ToolRunModel(
                id=f"tool-run:{plan.id}:{call.id}",
                analysis_id=plan.analysis_id,
                research_plan_id=plan.id,
                planned_call_id=call.id,
                capability=call.capability,
                query=call.query,
                required=call.required,
                provider="apify",
                actor_id=spec.actor_id,
                actor_build=spec.build,
                status="RUNNING",
                parameters=run_parameters,
                started_at=datetime.now(UTC),
            )
            self.session.add(model)
        else:
            model.status = "RUNNING"
            model.parameters = run_parameters
            model.error_code = None
            model.error_message = None
            model.started_at = datetime.now(UTC)
            model.finished_at = None
        await self.session.commit()
        return model

    @staticmethod
    def _error_code(exc: Exception) -> str:
        if isinstance(exc, ApifyTimeoutError):
            return "timeout"
        if isinstance(exc, ApifySchemaDriftError):
            return "schema_drift"
        if isinstance(exc, ApifyBudgetExceededError):
            return "budget_exceeded"
        if isinstance(exc, httpx.HTTPStatusError):
            return f"http_{exc.response.status_code}"
        if isinstance(exc, httpx.TransportError):
            return "transport_error"
        return "provider_error"

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        return str(exc).replace("\r", " ").replace("\n", " ")[:500]

    async def _checkpoint_failure(self, run: ToolRunModel, exc: Exception) -> None:
        if isinstance(exc, ApifyActorFailedError):
            run.provider_run_id = exc.run_id
        if isinstance(exc, ApifyTimeoutError) and exc.run_id:
            run.provider_run_id = exc.run_id
        if isinstance(exc, (ApifyTimeoutError, ApifySchemaDriftError)) and exc.run_data:
            run.provider_run_id = str(exc.run_data.get("id") or run.provider_run_id or "") or None
            run.dataset_id = exc.run_data.get("defaultDatasetId")
            cost = exc.run_data.get("usageTotalUsd", 0)
            run.cost_usd = float(cost) if isinstance(cost, int | float) else 0.0
        run.status = "FAILED"
        run.error_code = self._error_code(exc)
        run.error_message = self._safe_error(exc)
        run.finished_at = datetime.now(UTC)
        await self.session.commit()

    @classmethod
    def _source_url(cls, result: ApifyExecutionResult, item: dict[str, object]) -> str:
        video_url = item.get("videoUrl")
        if cls._is_usable_discovered_url("youtube_comments", video_url):
            for field_name in ("url", "pageUrl"):
                if cls._is_usable_discovered_url("youtube_comments", item.get(field_name)):
                    return str(item[field_name])
            return str(video_url)
        for field_name in (
            "url",
            "link",
            "jobUrl",
            "job_url",
            "linkedinUrl",
            "websiteUrl",
            "webVideoUrl",
            "videoUrl",
            "snapshotUrl",
            "pageUrl",
            "inputUrl",
            "channelUrl",
            "inputChannelUrl",
        ):
            value = item.get(field_name)
            if isinstance(value, str) and value.startswith(("https://", "http://")):
                return value
        snapshot = item.get("snapshot")
        if isinstance(snapshot, dict):
            for snap_field in ("link_url", "page_profile_uri"):
                snap_val = snapshot.get(snap_field)
                if isinstance(snap_val, str) and snap_val.startswith(("https://", "http://")):
                    return snap_val
        return f"https://api.apify.com/v2/datasets/{result.run.dataset_id}/items"

    @staticmethod
    def _title(call: PlannedToolCall, item: dict[str, object]) -> str:
        for field_name in (
            "title",
            "name",
            "pageName",
            "page_name",
            "companyName",
            "channelName",
            "positionName",
            "text",
            "caption",
            "comment",
            "channelDescription",
            "note",
        ):
            value = item.get(field_name)
            if isinstance(value, str) and value.strip():
                return value.strip()[:256]
        snapshot = item.get("snapshot")
        if isinstance(snapshot, dict):
            for snap_field in ("title", "page_name", "caption"):
                snap_val = snapshot.get(snap_field)
                if isinstance(snap_val, str) and snap_val.strip():
                    return snap_val.strip()[:256]
        organic = item.get("organicResults")
        if isinstance(organic, list) and organic and isinstance(organic[0], dict):
            org_title = organic[0].get("title")
            if isinstance(org_title, str) and org_title.strip():
                return org_title.strip()[:256]
        return f"{call.capability}: {call.query}"[:256]

    @classmethod
    def _comment_video_url(cls, item: dict[str, object], origin_urls: object) -> str | None:
        for key in ("url", "pageUrl", "videoUrl", "inputUrl"):
            if cls._is_usable_discovered_url("youtube_comments", item.get(key)):
                return str(item[key])
        origins = (
            [
                str(url)
                for url in origin_urls
                if cls._is_usable_discovered_url("youtube_comments", url)
            ]
            if isinstance(origin_urls, list)
            else []
        )
        video_id = item.get("videoId")
        if isinstance(video_id, str) and video_id.strip():
            for url in origins:
                parsed = urlsplit(url)
                origin_id = (
                    parsed.path.strip("/")
                    if (parsed.hostname or "").endswith("youtu.be")
                    else parse_qs(parsed.query).get("v", [""])[0]
                )
                if origin_id == video_id:
                    return url
            return None
        # An unspecified video can only be attributed when the call had one origin.
        return origins[0] if len(origins) == 1 else None

    @classmethod
    def _item_rejection_reason(
        cls, capability: str, item: dict[str, object], *, origin_urls: object = None
    ) -> str | None:
        if item.get("error") or item.get("errorMessage"):
            return "provider_error_item"
        if capability == "instagram":
            url = str(item.get("url") or item.get("inputUrl") or "")
            if "/explore/tags/" in url or "/explore/locations/" in url:
                return "directory_metadata"
            if not any(item.get(key) for key in ("caption", "shortCode", "text")):
                return "post_content_missing"
        if capability == "youtube_comments":
            if not any(
                isinstance(item.get(key), str) and str(item[key]).strip()
                for key in ("text", "comment")
            ):
                return "comment_content_missing"
            has_comment_id = any(item.get(key) for key in ("cid", "commentId"))
            has_video_id = isinstance(item.get("videoId"), str) and bool(
                str(item["videoId"]).strip()
            )
            has_video_url = any(
                cls._is_usable_discovered_url("youtube_comments", item.get(key))
                for key in ("url", "pageUrl", "videoUrl", "inputUrl")
            )
            has_channel_metadata = any(
                item.get(key)
                for key in ("channelUrl", "channelName", "channelId", "channelDescription")
            )
            if has_channel_metadata and not (has_comment_id or has_video_id or has_video_url):
                return "channel_metadata"
            if cls._comment_video_url(item, origin_urls) is None:
                return "comment_video_link_missing"
        if capability == "web_crawler":
            status_code = item.get("httpStatusCode") or item.get("statusCode") or item.get("status")
            if status_code in {404, "404"}:
                return "page_not_found"
            if status_code in {401, 403, "401", "403"}:
                return "page_blocked"
            title = str(item.get("title") or "").lower()
            text = str(item.get("text") or "").lower()
            if "404" in title or "não encontrada" in title or "not found" in title:
                return "page_not_found"
            if "não encontrada" in text[:300] and len(text) < 500:
                return "page_not_found"
        if capability == "tiktok" and not item.get("text"):
            return "video_content_missing"
        return None

    @classmethod
    def _normalized_items(
        cls, call: PlannedToolCall, result: ApifyExecutionResult
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        valid_children: list[dict[str, object]] = []
        rejected: list[dict[str, object]] = []
        for item in result.items:
            organic = item.get("organicResults")
            if call.capability == "google_search" and isinstance(organic, list):
                children = [
                    {
                        **entry,
                        "_discovery": {
                            "query": call.query,
                            "rank": entry.get("position", index + 1),
                            "serp_url": item.get("url"),
                            "planned_call_id": call.id,
                        },
                    }
                    for index, entry in enumerate(organic)
                    if isinstance(entry, dict)
                ]
                if not children:
                    rejected.append({"reason": "serp_without_organic_results", "item": item})
            else:
                children = [item]
            for child in children:
                reason = cls._item_rejection_reason(
                    call.capability, child, origin_urls=call.parameters.get("urls")
                )
                if not reason and call.capability == "youtube_comments":
                    source_video = cls._comment_video_url(child, call.parameters.get("urls"))
                    if source_video:
                        child = {**child, "videoUrl": source_video}
                    else:
                        reason = "comment_video_link_missing"
                if call.capability == "google_search":
                    if not cls._is_usable_discovered_url(
                        "web_crawler", child.get("url", child.get("link"))
                    ):
                        reason = "search_result_url_missing_or_invalid"
                    child = {
                        **child,
                        "_discovery": child.get(
                            "_discovery",
                            {
                                "query": call.query,
                                "rank": child.get("position"),
                                "planned_call_id": call.id,
                            },
                        ),
                    }
                if reason:
                    rejected.append({"reason": reason, "item": child})
                else:
                    valid_children.append(child)

        # Amostragem estratificada para YouTube com múltiplas URLs
        if call.capability == "youtube_comments":
            urls = call.parameters.get("urls")
            if isinstance(urls, list) and len(urls) > 1:
                video_groups: dict[str, list[dict[str, object]]] = {str(u): [] for u in urls}
                for child in valid_children:
                    v_url = str(child.get("videoUrl") or "")
                    if v_url in video_groups:
                        video_groups[v_url].append(child)
                    else:
                        video_groups.setdefault(v_url, []).append(child)

                per_video_quota = max(1, call.max_items // len(urls))
                items: list[dict[str, object]] = []
                leftovers: dict[str, list[dict[str, object]]] = {}
                for v_url, v_items in video_groups.items():
                    items.extend(v_items[:per_video_quota])
                    if len(v_items) > per_video_quota:
                        leftovers[v_url] = v_items[per_video_quota:]

                if len(items) < call.max_items:
                    while len(items) < call.max_items and any(leftovers.values()):
                        for v_url in list(leftovers.keys()):
                            if leftovers.get(v_url) and len(items) < call.max_items:
                                items.append(leftovers[v_url].pop(0))
                            if not leftovers.get(v_url):
                                leftovers.pop(v_url, None)

                return items[: call.max_items], rejected

        return valid_children[: call.max_items], rejected

    @classmethod
    def _build_sampling_audit(
        cls,
        *,
        call: PlannedToolCall,
        result: ApifyExecutionResult,
        retained_items: list[dict[str, object]],
        rejected_items: list[dict[str, object]],
    ) -> dict[str, Any]:
        limit_unit = CAPABILITY_LIMIT_UNITS.get(call.capability, "retained_total")
        dataset_total = result.total_items
        items_read = len(result.items)
        items_retained = len(retained_items)
        urls = call.parameters.get("urls")
        num_urls = len(urls) if isinstance(urls, list) else 1

        strategy = "top_n_budget_capped"
        quota_per_video = None
        distribution_per_video: dict[str, int] = {}

        if call.capability == "youtube_comments" and num_urls > 1:
            strategy = "stratified_per_video"
            quota_per_video = max(1, call.max_items // num_urls)
            for item in retained_items:
                v_url = str(item.get("videoUrl") or "")
                distribution_per_video[v_url] = distribution_per_video.get(v_url, 0) + 1

        truncation_detected = dataset_total > items_read
        truncation_reason = (
            f"O dataset da Apify continha {dataset_total} itens, mais itens que o limite lido de "
            f"{items_read} itens (critério: teto max_items={call.max_items}, unidade={limit_unit})."
            if truncation_detected
            else None
        )

        audit_data: dict[str, Any] = {
            "limit_unit": limit_unit,
            "dataset_total_items": dataset_total,
            "items_read": items_read,
            "items_retained": items_retained,
            "rejected_items_count": len(rejected_items),
            "sampling_strategy": strategy,
            "truncation_detected": truncation_detected,
            "truncation_reason": truncation_reason,
        }
        if quota_per_video is not None:
            audit_data["quota_per_video"] = quota_per_video
            audit_data["distribution_per_video"] = distribution_per_video
        return audit_data

    async def _persist_result(
        self,
        *,
        call: PlannedToolCall,
        run: ToolRunModel,
        result: ApifyExecutionResult,
    ) -> list[str]:
        spec = self.registry.require(call.capability)
        if result.run.actor_id != spec.actor_id or result.run.build_number != spec.build:
            raise ApifySchemaDriftError(
                "Executor retornou Actor ou build diferente da configuração autorizada."
            )

        items, rejected = self._normalized_items(call, result)
        candidates = [
            MarketEvidence.create(
                analysis_id=run.analysis_id,
                evidence_type=spec.evidence_type,
                source_name=f"apify_{call.capability}",
                source_url=self._source_url(result, item),
                collector=f"apify:{spec.actor_id}@{spec.build}",
                title=self._title(call, item),
                raw_payload=item,
            )
            for item in items
        ]
        sanitized = self.sanitizer.process_and_deduplicate(candidates)
        existing_hashes: set[str] = set()
        if sanitized:
            existing_hashes = set(
                (
                    await self.session.execute(
                        select(MarketEvidenceModel.content_hash).where(
                            MarketEvidenceModel.analysis_id == run.analysis_id,
                            MarketEvidenceModel.content_hash.in_(
                                [evidence.content_hash for evidence in sanitized]
                            ),
                        )
                    )
                ).scalars()
            )
        unique = [
            evidence for evidence in sanitized if evidence.content_hash not in existing_hashes
        ]
        evidence_cost = result.run.cost_usd / len(unique) if unique else 0.0
        for evidence in unique:
            self.session.add(
                MarketEvidenceModel(
                    id=evidence.id,
                    analysis_id=evidence.analysis_id,
                    tool_run_id=run.id,
                    evidence_type=evidence.evidence_type.value,
                    source_name=evidence.source_name,
                    source_url=evidence.source_url,
                    collector=evidence.collector,
                    content_hash=evidence.content_hash,
                    title=evidence.title,
                    raw_payload=evidence.raw_payload,
                    sanitized_data=evidence.sanitized_data,
                    quality_score=evidence.quality_score,
                    cost_usd=round(evidence_cost, 6),
                    collected_at=evidence.collected_at,
                )
            )

        run.provider_run_id = result.run.run_id
        run.dataset_id = result.run.dataset_id
        run.raw_items_count = len(result.items)
        run.valid_items_count = len(unique)
        run.cost_usd = result.run.cost_usd
        incomplete = result.run.incomplete_reason is not None
        run.status = "PARTIAL" if incomplete else "SUCCEEDED" if unique else "EMPTY"
        if incomplete:
            run.error_code = "timeout"
            run.error_message = result.run.incomplete_reason
        audit = dict(run.parameters)
        audit["provider_status"] = result.run.status
        audit["dataset_total_items"] = result.total_items
        audit["effective_actor_input"] = self.registry.build_input(call)
        audit["effective_scope"] = {
            "capability": call.capability,
            "geography": call.parameters.get("location") or call.parameters.get("country") or call.parameters.get("geo") or "Brasil",
            "time_window": call.parameters.get("time_range") or call.parameters.get("time_window") or call.parameters.get("date_posted"),
            "limit_unit": CAPABILITY_LIMIT_UNITS.get(call.capability, "retained_total"),
            "max_items": call.max_items,
            "query": call.query,
        }
        sampling_audit = self._build_sampling_audit(
            call=call,
            result=result,
            retained_items=items,
            rejected_items=rejected,
        )
        entity_keys = [extract_canonical_entity_id(call.capability, item) for item in items]
        unique_entity_keys = set(entity_keys)
        entity_audit = {
            "captures_count": len(items),
            "unique_entities_count": len(unique_entity_keys),
            "duplicate_captures_in_run": len(items) - len(unique_entity_keys),
            "entity_types": sorted({k.split(":", 1)[0] for k in unique_entity_keys}),
        }
        audit["sampling"] = sampling_audit
        audit["entities"] = entity_audit
        if call.capability == "web_crawler" or "urls" in call.parameters:
            target_urls = [str(u) for u in call.parameters.get("urls", []) if isinstance(u, str)]
            url_outcomes: dict[str, str] = {}
            for target in target_urls:
                target_can = self._canonical_url(target)
                matching_retained = next(
                    (
                        it
                        for it in items
                        if self._canonical_url(str(it.get("url") or it.get("inputUrl") or ""))
                        == target_can
                    ),
                    None,
                )
                matching_rejected = None
                for entry in rejected:
                    entry_item = entry.get("item")
                    if isinstance(entry_item, dict):
                        item_url = str(entry_item.get("url") or entry_item.get("inputUrl") or "")
                        if self._canonical_url(item_url) == target_can:
                            matching_rejected = entry
                            break
                if matching_retained:
                    url_outcomes[target] = "fetched"
                elif matching_rejected:
                    rej_reason = matching_rejected.get("reason", "")
                    if rej_reason == "page_not_found":
                        url_outcomes[target] = "not_found"
                    elif rej_reason == "page_blocked":
                        url_outcomes[target] = "blocked"
                    elif rej_reason == "unsupported_content_type":
                        url_outcomes[target] = "unsupported_type"
                    elif rej_reason == "provider_error_item":
                        url_outcomes[target] = "extraction_failed"
                    else:
                        url_outcomes[target] = "rejected"
                else:
                    url_outcomes[target] = (
                        "budget_skipped" if len(items) >= call.max_items else "not_found"
                    )
            audit["url_outcomes"] = url_outcomes
        audit["observation_status"] = (
            "observed_empty" if not result.items else "observed" if unique else "rejected_items"
        )
        audit["rejected_items_count"] = len(rejected)
        # Bounded raw snapshots retain provider errors/directories for audit without
        # presenting them as market evidence. Full raw dataset remains at dataset_id.
        audit["rejected_items"] = [
            {
                "reason": item["reason"],
                "raw_json": json.dumps(item["item"], ensure_ascii=False)[:4000],
            }
            for item in rejected[:10]
        ]
        run.parameters = audit
        run.finished_at = datetime.now(UTC)
        await self.session.commit()
        return [evidence.id for evidence in unique]

    async def collect(
        self,
        *,
        tenant_id: str,
        plan: CourseResearchPlan,
        understanding_snapshot: dict[str, object] | None = None,
    ) -> CollectionOutcome:
        dependency_ordered_calls = self._ordered_calls(plan)
        plan_model = await self._ensure_plan(
            tenant_id=tenant_id,
            plan=plan,
            understanding_snapshot=understanding_snapshot,
        )
        completed: list[str] = []
        evidence_ids: list[str] = []
        blocking: list[str] = []
        optional_failures: list[str] = []

        for call in dependency_ordered_calls:
            existing = await self._find_run(plan.id, call.id)
            if existing is not None and existing.status in {"SUCCEEDED", "PARTIAL"}:
                if existing.status == "PARTIAL":
                    optional_failures.append(call.id)
                else:
                    completed.append(call.id)
                evidence_ids.extend(
                    (
                        await self.session.execute(
                            select(MarketEvidenceModel.id).where(
                                MarketEvidenceModel.tool_run_id == existing.id
                            )
                        )
                    ).scalars()
                )
                continue
            # A terminal source result is reusable, including failures. Resuming
            # the workflow must not repeat paid calls to an unavailable source.
            if existing is not None and existing.status in {"EMPTY", "FAILED"}:
                if (existing.parameters or {}).get("observation_status") == "observed_empty":
                    completed.append(call.id)
                else:
                    optional_failures.append(call.id)
                continue

            remaining_budget = plan.budget_limit_usd - plan_model.spent_usd
            if remaining_budget <= 0:
                error = ApifyBudgetExceededError("Orçamento total da análise esgotado.")
                run = await self._checkpoint_running(plan=plan, call=call)
                await self._checkpoint_failure(run, error)
                optional_failures.append(call.id)
                continue

            run = await self._checkpoint_running(plan=plan, call=call)
            try:
                resolved_call = await self._resolve_dependent_urls(
                    call, analysis_id=plan.analysis_id, research_plan_id=plan.id
                )
                run.parameters = {
                    **run.parameters,
                    "resolved_urls": resolved_call.parameters.get("urls", []),
                }
                await self.session.commit()
                result = await self.executor.execute(
                    resolved_call,
                    max_total_charge_usd=remaining_budget,
                )
                # Charge the observed run atomically with its evidence/failure
                # checkpoint so retries cannot recover a stale, larger budget.
                plan_model.spent_usd = round(plan_model.spent_usd + result.run.cost_usd, 6)
                run.provider_run_id = result.run.run_id
                run.dataset_id = result.run.dataset_id
                run.cost_usd = result.run.cost_usd
                if result.run.cost_usd > remaining_budget + 0.000001:
                    raise ApifyBudgetExceededError(
                        "Custo real da run excedeu o orçamento restante autorizado."
                    )
                new_evidence_ids = await self._persist_result(
                    call=resolved_call,
                    run=run,
                    result=result,
                )
                evidence_ids.extend(new_evidence_ids)
                if run.status == "PARTIAL":
                    optional_failures.append(call.id)
                elif run.status == "EMPTY":
                    if run.parameters.get("observation_status") == "observed_empty":
                        completed.append(call.id)
                    else:
                        optional_failures.append(call.id)
                else:
                    completed.append(call.id)
                await self.session.commit()
            except (ApifyError, ActorConfigurationError, httpx.HTTPError, TimeoutError) as exc:
                if isinstance(exc, (ApifyTimeoutError, ApifySchemaDriftError)) and exc.run_data:
                    cost = exc.run_data.get("usageTotalUsd", 0)
                    if isinstance(cost, int | float):
                        plan_model.spent_usd = round(plan_model.spent_usd + cost, 6)
                await self._checkpoint_failure(run, exc)
                optional_failures.append(call.id)

        plan_model.status = "COMPLETED" if not optional_failures else "PARTIAL"
        await self.session.commit()
        return CollectionOutcome(
            research_plan_id=plan.id,
            completed_call_ids=completed,
            evidence_ids=evidence_ids,
            blocking_failures=blocking,
            optional_failures=optional_failures,
            spent_usd=plan_model.spent_usd,
        )
