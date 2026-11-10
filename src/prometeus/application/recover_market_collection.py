"""Execução persistida e recuperação delimitada da política collection-v2."""

from __future__ import annotations

import hashlib
import json
import math
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy import func, select

from prometeus.domain.collection_execution import collection_task_key
from prometeus.infrastructure.apify.client import (
    ApifyActorFailedError,
    ApifyClient,
    ApifyError,
    ApifyReconciliationRequiredError,
    ApifyTimeoutError,
)
from prometeus.infrastructure.apify.registry import ActorConfigurationError
from prometeus.infrastructure.db.models import (
    AnalysisModel,
    MarketEvidenceModel,
    ResearchPlanModel,
    ToolRunAttemptModel,
    ToolRunModel,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from prometeus.application.collect_market_evidence import (
        CollectionOutcome,
        CollectMarketEvidenceService,
    )
    from prometeus.domain.research import CourseResearchPlan


class CollectionRetryScheduled(RuntimeError):
    def __init__(self, next_attempt_at: datetime) -> None:
        self.next_attempt_at = next_attempt_at
        super().__init__(f"Recuperação da coleta agendada para {next_attempt_at.isoformat()}")


@dataclass(frozen=True)
class RecoveryDecision:
    cause: str
    action: str
    retry: bool = False
    delay_seconds: float = 2.0


def diagnose(error: Exception, attempt_index: int) -> RecoveryDecision:
    delay = min(60.0, 2**attempt_index + random.uniform(0, 1))
    if isinstance(error, ApifyReconciliationRequiredError):
        return RecoveryDecision("remote_result_uncertain", "reconcile_existing_run", True, delay)
    if isinstance(error, (ApifyActorFailedError, ApifyTimeoutError)) and error.dataset_read_pending:
        return RecoveryDecision("remote_dataset_unread", "reconcile_existing_run", True, delay)
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        try:
            body = error.response.json()
            kind = str(body.get("error", {}).get("type", "")) if isinstance(body, dict) else ""
        except (ValueError, AttributeError):
            kind = ""
        if status == 429:
            try:
                delay = max(delay, float(error.response.headers.get("Retry-After", "0")))
            except ValueError:
                pass
            return RecoveryDecision("rate_limit", "wait_and_reduce_concurrency", True, delay)
        if status == 402 and kind in {
            "actor-memory-limit-exceeded",
            "concurrent-runs-limit-exceeded",
        }:
            return RecoveryDecision(
                "account_resources_busy", "wait_for_resources", True, max(10, delay)
            )
        if status >= 500:
            return RecoveryDecision("provider_unavailable", "retry_after_backoff", True, delay)
        return RecoveryDecision("provider_configuration", "operator_configuration_required")
    if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout)):
        return RecoveryDecision("connection_not_established", "retry_after_backoff", True, delay)
    if isinstance(error, (ApifyActorFailedError, ApifyTimeoutError)):
        data = error.run_data or {}
        message = str(data.get("statusMessage") or str(error)).casefold()
        if any(
            term in message
            for term in (
                "unauthorized",
                "invalid token",
                "permission",
                "credits",
                "schema",
                "invalid input",
            )
        ):
            return RecoveryDecision("actor_configuration", "operator_configuration_required")
        if data.get("status") in {"FAILED", "TIMED-OUT", "ABORTED"}:
            return RecoveryDecision("actor_terminal_failure", "reduce_batch_and_retry", True, delay)
        return RecoveryDecision("remote_result_uncertain", "reconcile_existing_run", True, delay)
    return RecoveryDecision("invalid_contract_or_input", "operator_configuration_required")


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def collect_monitoring(
    service: CollectMarketEvidenceService,
    *,
    tenant_id: str,
    plan: CourseResearchPlan,
    understanding_snapshot: dict[str, object] | None,
    check_active: Callable[[], Awaitable[None]] | None,
) -> CollectionOutcome:
    from prometeus.application.collect_market_evidence import (
        CollectionOutcome,
        RequiredSourceBlockedError,
    )

    session = service.session
    owner = await session.scalar(
        select(AnalysisModel.tenant_id).where(AnalysisModel.id == plan.analysis_id)
    )
    if owner != tenant_id:
        raise ValueError("A análise não pertence à instituição solicitada.")
    plan_model = await service._ensure_plan(
        tenant_id=tenant_id, plan=plan, understanding_snapshot=understanding_snapshot
    )
    completed: list[str] = []
    failed: list[str] = []
    evidences: list[str] = []
    pending: list[datetime] = []
    uncertain: list[str] = []
    deferred_calls: set[str] = set()
    assert plan.execution_policy is not None

    for call in service._ordered_calls(plan):
        if check_active is not None:
            await check_active()
        if set(service._dependencies(call)) & deferred_calls:
            deferred_calls.add(call.id)
            continue
        task_key = collection_task_key(call)
        # Serialize task admission before any paid POST. The workflow lease is the
        # outer ownership boundary; this lock also protects concurrent collectors.
        await session.execute(
            select(AnalysisModel.id).where(AnalysisModel.id == plan.analysis_id).with_for_update()
        )
        attempts = list(
            (
                await session.execute(
                    select(ToolRunAttemptModel)
                    .where(
                        ToolRunAttemptModel.analysis_id == plan.analysis_id,
                        ToolRunAttemptModel.tenant_id == tenant_id,
                        ToolRunAttemptModel.task_key == task_key,
                    )
                    .order_by(ToolRunAttemptModel.attempt_index)
                    .execution_options(populate_existing=True)
                )
            ).scalars()
        )
        last = attempts[-1] if attempts else None
        run = (
            await session.get(ToolRunModel, last.tool_run_id)
            if last
            else await service._find_run(plan.id, call.id)
        )
        if run is not None and run.status in {"SUCCEEDED", "EMPTY", "PARTIAL"}:
            (
                failed
                if run.status == "PARTIAL"
                or run.parameters.get("observation_status") == "rejected_items"
                else completed
            ).append(call.id)
            evidences.extend(
                (
                    await session.execute(
                        select(MarketEvidenceModel.id).where(
                            MarketEvidenceModel.tool_run_id == run.id
                        )
                    )
                ).scalars()
            )
            await session.commit()
            continue
        if (
            last is not None
            and last.next_attempt_at
            and utc(last.next_attempt_at) > datetime.now(UTC)
        ):
            pending.append(utc(last.next_attempt_at))
            deferred_calls.add(call.id)
            await session.commit()
            continue
        if last is not None and last.status == "RUNNING" and utc(last.started_at) + timedelta(minutes=5) > datetime.now(UTC):
            pending.append(utc(last.started_at) + timedelta(minutes=5))
            deferred_calls.add(call.id)
            await session.commit()
            continue
        reconcile = last is not None and last.status in {"RUNNING", "IN_DOUBT"}
        if (
            last
            and not reconcile
            and (not last.next_attempt_at or len(attempts) >= plan.execution_policy.max_attempts)
        ):
            failed.append(call.id)
            await session.commit()
            continue
        if run is None:
            run = await service._checkpoint_running(plan=plan, call=call, commit=False)
        try:
            resolved = await service._resolve_dependent_urls(
                call, analysis_id=plan.analysis_id, research_plan_id=plan.id
            )
            if last and last.diagnosis.get("action") == "reduce_batch_and_retry":
                resolved = resolved.model_copy(
                    update={"max_items": max(1, resolved.max_items // (2 ** len(attempts)))}
                )
                if resolved.capability == "google_trends":
                    # The approved Actor launches browsers for these pages; reducing
                    # output items alone does not reduce its default concurrency (10).
                    resolved = resolved.model_copy(update={"parameters": {
                        **resolved.parameters, "recovery_max_concurrency": 1,
                    }})
                gap_urls = [url for url, status in (run.parameters.get("url_outcomes") or {}).items() if status in {"blocked", "extraction_failed", "budget_skipped"}]
                if gap_urls and resolved.parameters.get("urls"):
                    resolved = resolved.model_copy(update={"parameters": {**resolved.parameters, "urls": [url for url in resolved.parameters["urls"] if url in gap_urls][:resolved.max_items]}})
            actor_input = service.registry.build_input(resolved)
        except ActorConfigurationError as error:
            from prometeus.application.collect_market_evidence import NoDiscoveredUrlError

            dependencies = service._dependencies(call)
            parents = list((await session.execute(select(ToolRunModel).where(
                ToolRunModel.analysis_id == plan.analysis_id,
                ToolRunModel.research_plan_id == plan.id,
                ToolRunModel.planned_call_id.in_(dependencies),
            ))).scalars()) if dependencies else []
            if isinstance(error, NoDiscoveredUrlError) and call.parameters.get("competitor_id") and len(parents) == len(dependencies) and parents and all(
                parent.status in {"SUCCEEDED", "EMPTY"}
                and parent.parameters.get("observation_status") in {"observed", "observed_empty"}
                for parent in parents
            ):
                run.status = "EMPTY"
                run.parameters = {**run.parameters, "observation_status": "no_candidates_to_validate", "cost_status": "not_incurred", "spending_mode": "monitor_only"}
                run.finished_at = datetime.now(UTC)
                completed.append(call.id)
                await session.commit()
                continue
            await service._checkpoint_failure(run, error)
            run.parameters = {
                **run.parameters,
                "recovery_action": "operator_configuration_required",
                "spending_mode": "monitor_only",
            }
            failed.append(call.id)
            await session.commit()
            continue
        if reconcile:
            assert last is not None
            attempt = last
            reads = int(attempt.diagnosis.get("reconciliation_attempts", 0))
            if reads >= 3:
                uncertain.append(call.id)
                await session.commit()
                continue
            attempt.diagnosis = {**attempt.diagnosis, "reconciliation_attempts": reads + 1}
        else:
            spec = service.registry.require(call.capability)
            attempt = ToolRunAttemptModel(
                id=str(uuid.uuid4()),
                tool_run_id=run.id,
                analysis_id=plan.analysis_id,
                tenant_id=tenant_id,
                task_key=task_key,
                attempt_index=len(attempts) + 1,
                input_hash=hashlib.sha256(
                    json.dumps(actor_input, sort_keys=True).encode()
                ).hexdigest(),
                actor_id=spec.actor_id,
                actor_build=spec.build,
                status="RUNNING",
                input_snapshot=actor_input,
                diagnosis={},
                started_at=datetime.now(UTC),
            )
            session.add(attempt)
        run.status = "RUNNING"
        run.parameters = {
            **run.parameters,
            "spending_mode": "monitor_only",
            "authorization_policy": "collection-v2",
            "authorization_status": "scope_authorized",
            "authorized_cap_usd": None,
            "active_attempt_id": attempt.id,
            "attempts_count": attempt.attempt_index,
            "resolved_urls": resolved.parameters.get("urls", []),
        }
        await session.commit()

        async def started(
            data: dict[str, Any], attempt: ToolRunAttemptModel = attempt, run: ToolRunModel = run
        ) -> None:
            if not data.get("id"):
                raise ApifyReconciliationRequiredError("Início remoto sem identificação.")
            attempt.provider_run_id = str(data["id"])
            attempt.dataset_id = data.get("defaultDatasetId")
            run.provider_run_id = attempt.provider_run_id
            run.dataset_id = attempt.dataset_id
            await session.commit()

        try:
            if check_active is not None:
                await check_active()
            if reconcile:
                if not isinstance(service.executor, ApifyClient):
                    raise ApifyReconciliationRequiredError(
                        "Executor não oferece reconciliação de run existente."
                    )
                if not attempt.provider_run_id:
                    located = await service.executor.find_started_run(
                        resolved,
                        started_at=utc(attempt.started_at),
                        actor_input=attempt.input_snapshot,
                    )
                    if located:
                        await started(located)
                if not attempt.provider_run_id:
                    raise ApifyReconciliationRequiredError(
                        "Não foi possível identificar inequivocamente a execução remota."
                    )
                result = await service.executor.resume(resolved, run_id=attempt.provider_run_id)
            elif isinstance(service.executor, ApifyClient):
                result = await service.executor.execute(
                    resolved, max_total_charge_usd=None, on_run_started=started
                )
            else:
                result = await service.executor.execute(resolved, max_total_charge_usd=None)
            attempt.provider_run_id = result.run.run_id
            attempt.dataset_id = result.run.dataset_id
            attempt.cost_usd = result.run.cost_usd if result.run.cost_status != "pending" else None
            attempt.status = "SUCCEEDED" if not result.run.incomplete_reason else "PARTIAL"
            attempt.finished_at = datetime.now(UTC)
            attempt.next_attempt_at = None
            run.provider_run_id = result.run.run_id
            run.dataset_id = result.run.dataset_id
            run.error_code = None
            run.error_message = None
            previous_outcomes = dict(run.parameters.get("url_outcomes") or {})
            evidences.extend(
                await service._persist_result(call=resolved, run=run, result=result, commit=False)
            )
            outcomes = {**previous_outcomes, **(run.parameters.get("url_outcomes") or {})}
            run.parameters = {**run.parameters, **({"url_outcomes": outcomes} if outcomes else {})}
            rejected = run.parameters.get("rejected_items") or []
            permanent_diagnostic = any(
                item.get("reason") in {"page_blocked", "provider_error_item"}
                and any(pattern in str(item.get("raw_json", "")).casefold() for pattern in (
                    "invalid token", "invalid api key", "unauthorized", "insufficient credits",
                    "credit exhausted", "missing credentials", "insufficient permissions",
                    "not enough usage",
                ))
                for item in rejected if isinstance(item, dict)
            )
            provider_diagnostic = any(
                item.get("reason") in {"page_blocked", "provider_error_item"}
                and "no_items" not in str(item.get("raw_json", "")).casefold()
                for item in rejected if isinstance(item, dict)
            )
            gaps = any(status in {"blocked", "extraction_failed", "budget_skipped"} for status in outcomes.values())
            retained_count = int(await session.scalar(select(func.count()).select_from(MarketEvidenceModel).where(MarketEvidenceModel.tool_run_id == run.id)) or 0)
            run.valid_items_count = retained_count
            if provider_diagnostic or gaps or result.run.incomplete_reason:
                attempt.status = "PARTIAL" if retained_count else "FAILED"
                action = "operator_configuration_required" if permanent_diagnostic else "reduce_batch_and_retry"
                attempt.diagnosis = {**attempt.diagnosis, "cause": "provider_dataset_blocked", "action": action, "url_outcomes": outcomes}
                run.error_code = "provider_dataset_blocked"
                run.error_message = "O Actor terminou, mas parte da coleta foi bloqueada ou não pôde ser extraída."
                run.parameters = {**run.parameters, "recovery_action": action, "recovery_cause": "provider_dataset_blocked"}
                if not permanent_diagnostic and attempt.attempt_index < plan.execution_policy.max_attempts:
                    attempt.next_attempt_at = datetime.now(UTC) + timedelta(seconds=2**attempt.attempt_index)
                    pending.append(attempt.next_attempt_at)
                    deferred_calls.add(call.id)
                    run.status = "RETRY_SCHEDULED"
                else:
                    run.status = "PARTIAL" if retained_count else "FAILED"
                    failed.append(call.id)
            else:
                if retained_count:
                    run.status = "SUCCEEDED"
                    run.parameters = {**run.parameters, "observation_status": "observed"}
                (failed if run.parameters.get("observation_status") == "rejected_items" else completed).append(call.id)
        except (ApifyError, ActorConfigurationError, httpx.HTTPError, TimeoutError) as error:
            decision = diagnose(error, attempt.attempt_index)
            if reconcile and not isinstance(error, (ApifyActorFailedError, ApifyTimeoutError)):
                decision = RecoveryDecision(
                    "remote_result_uncertain", "reconcile_existing_run", True, 5
                )
            data = getattr(error, "run_data", None) or {}
            if data.get("id"):
                attempt.provider_run_id = str(data["id"])
                attempt.dataset_id = data.get("defaultDatasetId")
            cost = data.get("usageTotalUsd")
            if (
                isinstance(cost, int | float)
                and not isinstance(cost, bool)
                and math.isfinite(cost)
                and cost >= 0
            ):
                attempt.cost_usd = cost
            await service._checkpoint_failure(run, error)
            attempt.status = "IN_DOUBT" if decision.action == "reconcile_existing_run" else "FAILED"
            attempt.finished_at = datetime.now(UTC)
            attempt.diagnosis = {
                **attempt.diagnosis,
                "cause": decision.cause,
                "action": decision.action,
                **({"provider_error_code": error.provider_error_code, "provider_error_message": error.provider_error_message} if hasattr(error, "provider_error_code") and hasattr(error, "provider_error_message") else {}),
            }
            run.parameters = {
                **run.parameters,
                "recovery_action": decision.action,
                "recovery_cause": decision.cause,
            }
            allowance = (
                int(attempt.diagnosis.get("reconciliation_attempts", 0)) < 3
                if attempt.status == "IN_DOUBT"
                else attempt.attempt_index < plan.execution_policy.max_attempts
            )
            if decision.retry and allowance:
                attempt.next_attempt_at = datetime.now(UTC) + timedelta(
                    seconds=decision.delay_seconds
                )
                pending.append(attempt.next_attempt_at)
                deferred_calls.add(call.id)
                run.status = "IN_DOUBT" if attempt.status == "IN_DOUBT" else "RETRY_SCHEDULED"
            else:
                attempt.next_attempt_at = None
                (uncertain if attempt.status == "IN_DOUBT" else failed).append(call.id)
        await session.flush()
        run.cost_usd = float(
            await session.scalar(
                select(func.sum(ToolRunAttemptModel.cost_usd)).where(
                    ToolRunAttemptModel.tool_run_id == run.id
                )
            )
            or 0
        )
        await session.flush()
        origin = await session.get(ResearchPlanModel, run.research_plan_id)
        if origin is not None:
            origin.spent_usd = float(
                await session.scalar(
                    select(func.sum(ToolRunModel.cost_usd)).where(
                        ToolRunModel.research_plan_id == origin.id
                    )
                )
                or 0
            )
        await session.commit()
    plan_model.status = (
        "IN_PROGRESS" if pending or uncertain else "PARTIAL" if failed else "COMPLETED"
    )
    await session.commit()
    if pending:
        raise CollectionRetryScheduled(min(pending))
    if uncertain:
        raise RequiredSourceBlockedError(
            uncertain[0],
            "Execução remota permanece incerta após reconciliação; demais fontes foram preservadas.",
        )
    return CollectionOutcome(
        research_plan_id=plan.id,
        completed_call_ids=completed,
        evidence_ids=evidences,
        optional_failures=failed,
        spent_usd=plan_model.spent_usd,
    )
