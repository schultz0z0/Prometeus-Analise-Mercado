"""Execução persistente do plano de pesquisa, sem qualquer fallback sintético."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.application.sanitization import EvidenceSanitizer
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
        hostname = (urlsplit(value).hostname or "").lower()
        if not hostname or hostname == "api.apify.com":
            return False
        if capability == "youtube_comments":
            return (
                hostname == "youtu.be"
                or hostname.endswith(".youtube.com")
                or hostname == "youtube.com"
            )
        return True

    async def _resolve_dependent_urls(
        self, call: PlannedToolCall, *, analysis_id: str
    ) -> PlannedToolCall:
        if call.capability not in {"web_crawler", "youtube_comments"}:
            return call
        supplied = call.parameters.get("urls", call.parameters.get("start_urls", []))
        if isinstance(supplied, str):
            supplied = [supplied]
        if isinstance(supplied, list) and any(
            self._is_usable_discovered_url(call.capability, value) for value in supplied
        ):
            return call

        evidence_rows = (
            (
                await self.session.execute(
                    select(MarketEvidenceModel)
                    .where(MarketEvidenceModel.analysis_id == analysis_id)
                    .order_by(MarketEvidenceModel.collected_at, MarketEvidenceModel.id)
                )
            )
            .scalars()
            .all()
        )
        discovered: list[str] = []
        for evidence in evidence_rows:
            candidates: list[object] = [evidence.source_url]
            for payload in (evidence.sanitized_data, evidence.raw_payload):
                if isinstance(payload, dict):
                    candidates.extend(
                        payload.get(key) for key in ("url", "link", "videoUrl", "webVideoUrl")
                    )
            for candidate in candidates:
                if (
                    self._is_usable_discovered_url(call.capability, candidate)
                    and candidate not in discovered
                ):
                    discovered.append(str(candidate))
        if not discovered:
            raise ActorConfigurationError(
                f"A capability '{call.capability}' não recebeu URL e nenhuma URL compatível "
                "foi descoberta por uma busca anterior."
            )
        parameters = dict(call.parameters)
        parameters["urls"] = discovered[: call.max_items]
        return call.model_copy(update={"parameters": parameters})

    async def _checkpoint_running(
        self,
        *,
        plan: CourseResearchPlan,
        call: PlannedToolCall,
    ) -> ToolRunModel:
        spec = self.registry.require(call.capability)
        model = await self._find_run(plan.id, call.id)
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
                parameters=call.parameters,
                started_at=datetime.now(UTC),
            )
            self.session.add(model)
        else:
            model.status = "RUNNING"
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
        run.status = "FAILED"
        run.error_code = self._error_code(exc)
        run.error_message = self._safe_error(exc)
        run.finished_at = datetime.now(UTC)
        await self.session.commit()

    @staticmethod
    def _source_url(result: ApifyExecutionResult, item: dict[str, object]) -> str:
        for field_name in (
            "url",
            "link",
            "jobUrl",
            "linkedinUrl",
            "webVideoUrl",
            "snapshotUrl",
        ):
            value = item.get(field_name)
            if isinstance(value, str) and value.startswith(("https://", "http://")):
                return value
        return f"https://api.apify.com/v2/datasets/{result.run.dataset_id}/items"

    @staticmethod
    def _title(call: PlannedToolCall, item: dict[str, object]) -> str:
        for field_name in ("title", "name", "pageName", "positionName"):
            value = item.get(field_name)
            if isinstance(value, str) and value.strip():
                return value.strip()[:256]
        return f"{call.capability}: {call.query}"[:256]

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
            for item in result.items
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
        run.raw_items_count = result.total_items
        run.valid_items_count = len(unique)
        run.cost_usd = result.run.cost_usd
        run.status = "SUCCEEDED" if unique else "EMPTY"
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
        plan_model = await self._ensure_plan(
            tenant_id=tenant_id,
            plan=plan,
            understanding_snapshot=understanding_snapshot,
        )
        completed: list[str] = []
        evidence_ids: list[str] = []
        blocking: list[str] = []
        optional_failures: list[str] = []

        dependency_ordered_calls = sorted(
            plan.tool_calls,
            key=lambda item: item.capability in {"web_crawler", "youtube_comments"},
        )
        for call in dependency_ordered_calls:
            existing = await self._find_run(plan.id, call.id)
            if existing is not None and existing.status == "SUCCEEDED":
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
            if existing is not None and existing.status == "EMPTY":
                if call.required:
                    blocking.append(call.id)
                    raise RequiredSourceBlockedError(call.id, "dataset vazio")
                optional_failures.append(call.id)
                continue

            remaining_budget = plan.budget_limit_usd - plan_model.spent_usd
            if remaining_budget <= 0:
                error = ApifyBudgetExceededError("Orçamento total da análise esgotado.")
                run = await self._checkpoint_running(plan=plan, call=call)
                await self._checkpoint_failure(run, error)
                if call.required:
                    blocking.append(call.id)
                    raise RequiredSourceBlockedError(call.id, str(error)) from error
                optional_failures.append(call.id)
                continue

            run = await self._checkpoint_running(plan=plan, call=call)
            try:
                resolved_call = await self._resolve_dependent_urls(
                    call, analysis_id=plan.analysis_id
                )
                result = await self.executor.execute(
                    resolved_call,
                    max_total_charge_usd=remaining_budget,
                )
                if result.run.cost_usd > remaining_budget + 0.000001:
                    raise ApifyBudgetExceededError(
                        "Custo real da run excedeu o orçamento restante autorizado."
                    )
                new_evidence_ids = await self._persist_result(
                    call=resolved_call,
                    run=run,
                    result=result,
                )
                plan_model.spent_usd = round(plan_model.spent_usd + result.run.cost_usd, 6)
                evidence_ids.extend(new_evidence_ids)
                if run.status == "EMPTY":
                    if call.required:
                        blocking.append(call.id)
                        plan_model.status = "BLOCKED"
                        await self.session.commit()
                        raise RequiredSourceBlockedError(call.id, "dataset vazio")
                    optional_failures.append(call.id)
                else:
                    completed.append(call.id)
                await self.session.commit()
            except RequiredSourceBlockedError:
                raise
            except (ApifyError, ActorConfigurationError, httpx.HTTPError) as exc:
                await self._checkpoint_failure(run, exc)
                if call.required:
                    blocking.append(call.id)
                    plan_model.status = "BLOCKED"
                    await self.session.commit()
                    raise RequiredSourceBlockedError(call.id, str(exc)) from exc
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
