"""Cliente Apify assíncrono com Actors pinados, orçamento e proveniência real."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable
from contextlib import suppress
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote_plus

import httpx

from prometeus.domain.configuration import AppSettings
from prometeus.domain.ports.market_sources import (
    EvidenceType,
    MarketEvidence,
    MarketSourcePort,
    ResearchPlan,
)
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.apify.schemas import (
    ApifyExecutionResult,
    ApifyRunMetadata,
    validate_dataset_items,
)


class ApifyError(RuntimeError):
    """Erro base sanitizado da integração Apify."""


class ApifyRequestRejectedError(httpx.HTTPStatusError):
    """Motivo de rejeição anterior à execução, com token removido."""

    def __init__(self, error: httpx.HTTPStatusError, *, token: str) -> None:
        try:
            payload = error.response.json()
            detail = payload.get("error") if isinstance(payload, dict) else None
            detail = detail if isinstance(detail, dict) else {}
        except ValueError:
            detail = {}
        self.provider_error_code = str(detail.get("type") or "request_rejected")[:128]
        message = str(detail.get("message") or "O provedor rejeitou a solicitação.")
        if token:
            message = message.replace(token, "[redacted]")
        self.provider_error_message = message.replace("\r", " ").replace("\n", " ")[:500]
        super().__init__(f"Apify HTTP {error.response.status_code} [{self.provider_error_code}]: {self.provider_error_message}", request=error.request, response=error.response)


class ApifyBudgetExceededError(ApifyError):
    """A chamada ultrapassaria o orçamento autorizado."""


class ApifyTimeoutError(ApifyError):
    """A run não alcançou estado terminal no limite de polling."""

    def __init__(
        self,
        message: str,
        *,
        run_id: str | None = None,
        run_data: dict[str, Any] | None = None,
    ) -> None:
        self.run_id = run_id
        self.run_data = run_data
        self.dataset_result: ApifyExecutionResult | None = None
        self.dataset_read_pending = False
        super().__init__(message)


class ApifySchemaDriftError(ApifyError):
    """Resposta da Apify ou dataset divergiu do contrato esperado."""

    def __init__(
        self, message: str, *, run_data: dict[str, Any] | None = None,
        dataset_result: ApifyExecutionResult | None = None,
    ) -> None:
        self.run_data = run_data
        self.dataset_result = dataset_result
        super().__init__(message)


class ApifyReconciliationRequiredError(ApifySchemaDriftError):
    """Execução remota ou cobrança indeterminada; não autoriza nova compra."""


class ApifyActorFailedError(ApifyError):
    """A run terminou em um estado de falha explícito."""

    def __init__(
        self, *, run_id: str, status: str, message: str = "", run_data: dict[str, Any] | None = None
    ) -> None:
        self.run_id = run_id
        self.status = status
        self.run_data = run_data
        self.dataset_result: ApifyExecutionResult | None = None
        self.dataset_read_pending = False
        safe_message = message.strip().replace("\r", " ").replace("\n", " ")[:500]
        detail = f": {safe_message}" if safe_message else ""
        super().__init__(f"Run Apify {run_id} terminou com status {status}{detail}")


TERMINAL_STATUSES = frozenset({"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"})
FAILED_STATUSES = TERMINAL_STATUSES - {"SUCCEEDED"}
_READ_RETRIES: ContextVar[int] = ContextVar("apify_read_retries", default=3)


class ApifyClient:
    """Executa uma chamada planejada sem permitir escolha livre de Actor."""

    def __init__(
        self,
        *,
        api_token: str,
        registry: ApifyActorRegistry,
        base_url: str = "https://api.apify.com/v2",
        timeout_seconds: float = 30.0,
        polling_interval_seconds: float = 1.0,
        max_poll_attempts: int = 300,
        wait_for_finish_seconds: int = 10,
        http_client: httpx.AsyncClient | None = None,
        cancellation_check: Callable[[], Awaitable[bool]] | None = None,
    ) -> None:
        if not api_token.strip():
            raise ApifyError("Token Apify não configurado.")
        self._api_token = api_token.strip()
        self.registry = registry
        self.base_url = base_url.rstrip("/")
        self.polling_interval_seconds = polling_interval_seconds
        self.max_poll_attempts = max_poll_attempts
        self.wait_for_finish_seconds = max(0, min(wait_for_finish_seconds, 60))
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self.cancellation_check = cancellation_check

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_token}",
        }

    async def _get(self, url: str, *, retry_limit: int | None = None, **kwargs: Any) -> httpx.Response:
        """Recupera leituras sem iniciar novamente um Actor pago."""
        retries = _READ_RETRIES.get() if retry_limit is None else retry_limit
        for attempt in range(retries + 1):
            if self.cancellation_check is not None and not await self.cancellation_check():
                raise asyncio.CancelledError()
            try:
                response = await self._client.get(url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPError as exc:
                transient = not isinstance(exc, httpx.HTTPStatusError) or (
                    exc.response.status_code == 429 or exc.response.status_code >= 500
                )
                if not transient or attempt == retries:
                    raise
                delay = min(30.0, self.polling_interval_seconds * (2**attempt))
                if isinstance(exc, httpx.HTTPStatusError):
                    try:
                        requested_delay = float(exc.response.headers.get("Retry-After", "0"))
                    except ValueError:
                        requested_delay = 0
                    if requested_delay > 30:
                        raise
                    delay = max(delay, requested_delay)
                await asyncio.sleep(delay)
        raise AssertionError("unreachable")

    @staticmethod
    def _run_data(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ApifySchemaDriftError("A API Apify retornou JSON inválido.") from exc
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise ApifySchemaDriftError("A API Apify não retornou o objeto data esperado.")
        return data

    @staticmethod
    def _ensure_success_or_raise(run_data: dict[str, Any]) -> None:
        status = str(run_data.get("status", ""))
        if status in FAILED_STATUSES:
            raise ApifyActorFailedError(
                run_id=str(run_data.get("id", "unknown")),
                status=status,
                message=str(run_data.get("statusMessage", "")),
                run_data=run_data,
            )

    async def _wait_for_terminal(self, run_data: dict[str, Any]) -> dict[str, Any]:
        run_id = str(run_data.get("id", ""))
        if not run_id:
            raise ApifySchemaDriftError("A resposta de início não contém run id.")

        self._ensure_success_or_raise(run_data)
        if run_data.get("status") == "SUCCEEDED":
            return run_data

        poll_url = f"{self.base_url}/actor-runs/{run_id}"
        for _ in range(self.max_poll_attempts):
            if self.cancellation_check is not None and not await self.cancellation_check():
                aborted = await self._client.post(f"{poll_url}/abort", headers=self._headers)
                aborted.raise_for_status()
                abort_data = self._run_data(aborted)
                raise ApifyTimeoutError(
                    "Análise cancelada; aborto do Actor solicitado.",
                    run_id=run_id,
                    run_data=abort_data,
                )
            await asyncio.sleep(self.polling_interval_seconds)
            response = await self._get(poll_url, headers=self._headers)
            response.raise_for_status()
            run_data = self._run_data(response)
            self._ensure_success_or_raise(run_data)
            if run_data.get("status") == "SUCCEEDED":
                return run_data
        # A local timeout must not leave a paid Actor running indefinitely.
        cancellation = "Cancelamento remoto não confirmado; requer reconciliação."
        terminal_data = run_data
        try:
            aborted = await self._client.post(f"{poll_url}/abort", headers=self._headers)
            aborted.raise_for_status()
            abort_data = self._run_data(aborted)
            terminal_data = abort_data
            if abort_data.get("status") == "ABORTED":
                cancellation = "Cancelamento remoto confirmado."
        except (httpx.HTTPError, ApifySchemaDriftError):
            pass
        raise ApifyTimeoutError(
            f"Run Apify {run_id} não terminou após {self.max_poll_attempts} consultas. {cancellation}",
            run_id=run_id,
            run_data=terminal_data,
        )

    async def _resolve_missing_build(self, run_data: dict[str, Any]) -> dict[str, Any]:
        number = run_data.get("buildNumber")
        if isinstance(number, str) and number.strip():
            return run_data
        run_id = run_data.get("id")
        if not run_id:
            raise ApifySchemaDriftError(
                "A run não contém identificador para conferir o build.", run_data=run_data
            )
        try:
            response = await self._get(
                f"{self.base_url}/actor-runs/{run_id}", headers=self._headers
            )
            response.raise_for_status()
            refreshed = self._run_data(response)
            if (
                refreshed.get("id") != run_id
                or refreshed.get("status") not in TERMINAL_STATUSES
                or refreshed.get("status") != run_data.get("status")
                or refreshed.get("defaultDatasetId") != run_data.get("defaultDatasetId")
            ):
                raise ApifySchemaDriftError(
                    "Não foi possível confirmar a identidade e o término da run."
                )
            if (
                not isinstance(refreshed.get("buildNumber"), str)
                or not refreshed["buildNumber"].strip()
            ):
                build_id = refreshed.get("buildId")
                if not build_id:
                    raise ApifySchemaDriftError(
                        "A run não contém buildNumber nem buildId verificável."
                    )
                response = await self._get(
                    f"{self.base_url}/actor-builds/{build_id}", headers=self._headers
                )
                response.raise_for_status()
                build = self._run_data(response)
                if (
                    build.get("id") != build_id
                    or not refreshed.get("actId")
                    or build.get("actId") != refreshed["actId"]
                ):
                    raise ApifySchemaDriftError("O build não corresponde ao Actor da run.")
                refreshed = {**refreshed, "buildNumber": build.get("buildNumber")}
            return refreshed
        except (httpx.HTTPError, ApifySchemaDriftError) as exc:
            raise ApifySchemaDriftError(
                "Não foi possível verificar o build real da run.", run_data=run_data
            ) from exc

    async def _reconcile_billing(self, run_data: dict[str, Any]) -> dict[str, Any]:
        def valid_cost(data: dict[str, Any]) -> bool:
            cost = data.get("usageTotalUsd")
            return (
                isinstance(cost, int | float)
                and not isinstance(cost, bool)
                and math.isfinite(cost)
                and cost >= 0
            )

        pricing = run_data.get("pricingInfo") or {}
        if not isinstance(pricing, dict):
            raise ApifyReconciliationRequiredError(
                "Metadados de cobrança inválidos; requer reconciliação.", run_data=run_data
            )
        per_event = pricing.get("pricingModel") == "PAY_PER_EVENT"
        if not per_event and valid_cost(run_data):
            return run_data
        original = run_data
        for attempt in range(5):
            try:
                response = await self._get(
                    f"{self.base_url}/actor-runs/{original['id']}", headers=self._headers
                )
                response.raise_for_status()
                current = self._run_data(response)
                if (
                    current.get("id") != original["id"]
                    or current.get("defaultDatasetId") != original.get("defaultDatasetId")
                    or current.get("status") not in TERMINAL_STATUSES
                    or current.get("status") != original.get("status")
                    or (
                        current.get("buildNumber")
                        and current["buildNumber"] != original.get("buildNumber")
                    )
                ):
                    raise ApifyReconciliationRequiredError(
                        "Identidade ou estado remoto mudou; requer reconciliação.",
                        run_data=original,
                    )
                run_data = current
                if not current.get("buildNumber") and original.get("buildNumber"):
                    if (
                        not original.get("buildId")
                        or current.get("buildId") != original["buildId"]
                        or current.get("actId") != original.get("actId")
                    ):
                        raise ApifyReconciliationRequiredError(
                            "Build sem identidade verificável durante cobrança; requer reconciliação.",
                            run_data=original,
                        )
                    current = {**current, "buildNumber": original["buildNumber"]}
                    run_data = current
                charged = current.get("chargedEventCounts")
                accounted = current.get("accountedChargedEventCounts")
                pricing = current.get("pricingInfo") or {}
                if not isinstance(pricing, dict):
                    continue
                current_per_event = pricing.get("pricingModel") == "PAY_PER_EVENT"
                if per_event and not current_per_event:
                    continue
                if (
                    not current_per_event
                    or (
                        isinstance(charged, dict)
                        and isinstance(accounted, dict)
                        and all(
                            isinstance(count, int)
                            and not isinstance(count, bool)
                            and count >= 0
                            and isinstance(accounted.get(event), int)
                            and not isinstance(accounted[event], bool)
                            and accounted[event] >= count
                            for event, count in charged.items()
                        )
                    )
                ) and valid_cost(current):
                    return current
            except ApifyReconciliationRequiredError:
                raise
            except (httpx.HTTPError, ApifySchemaDriftError):
                pass
            if attempt < 4:
                await asyncio.sleep(self.polling_interval_seconds)
        raise ApifyReconciliationRequiredError(
            "Cobrança Apify ainda não confirmada; requer reconciliação antes de nova coleta.",
            run_data=run_data,
        )

    async def execute(
        self,
        call: PlannedToolCall,
        *,
        max_total_charge_usd: float | None,
        on_run_started: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> ApifyExecutionResult:
        if max_total_charge_usd is not None and max_total_charge_usd <= 0:
            raise ApifyBudgetExceededError("A chamada Apify não possui orçamento positivo.")

        spec = self.registry.require(call.capability)
        actor_input = self.registry.build_input(call)
        start_url = f"{self.base_url}/actors/{spec.actor_path}/runs"
        try:
            response = await self._client.post(
                start_url,
                params={
                    "build": spec.build,
                    "waitForFinish": self.wait_for_finish_seconds,
                    **({"maxItems": call.max_items, "maxTotalChargeUsd": max_total_charge_usd} if max_total_charge_usd is not None else {}),
                    "restartOnError": "false",
                },
                json=actor_input,
                headers=self._headers,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout)):
                raise
            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code < 500 and error.response.status_code != 408:
                raise ApifyRequestRejectedError(error, token=self._api_token) from error
            raise ApifyReconciliationRequiredError(
                "Início remoto sem confirmação; custo e execução exigem reconciliação."
            ) from error
        try:
            started_data = self._run_data(response)
        except ApifySchemaDriftError as error:
            raise ApifyReconciliationRequiredError(
                "Resposta de início inválida; execução remota requer reconciliação."
            ) from error
        if on_run_started is not None:
            await on_run_started(started_data)
        token = _READ_RETRIES.set(0 if max_total_charge_usd is None else 3)
        try:
            return await self._finish_execution(call, started_data, monitoring=max_total_charge_usd is None)
        finally:
            _READ_RETRIES.reset(token)

    async def resume(self, call: PlannedToolCall, *, run_id: str) -> ApifyExecutionResult:
        try:
            response = await self._get(f"{self.base_url}/actor-runs/{run_id}", retry_limit=0, headers=self._headers)
        except asyncio.CancelledError:
            with suppress(httpx.HTTPError):
                await self._client.post(f"{self.base_url}/actor-runs/{run_id}/abort", headers=self._headers)
            raise
        data = self._run_data(response)
        if data.get("id") != run_id:
            raise ApifyReconciliationRequiredError("Identidade remota divergente na retomada.")
        token = _READ_RETRIES.set(0)
        try:
            return await self._finish_execution(call, data, monitoring=True)
        finally:
            _READ_RETRIES.reset(token)

    async def find_started_run(
        self, call: PlannedToolCall, *, started_at: datetime, actor_input: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Reconcilia início ambíguo; ausência ou ambiguidade não autoriza novo POST."""
        spec = self.registry.require(call.capability)
        response = await self._get(
            f"{self.base_url}/actors/{spec.actor_path}/runs",
            params={"desc": "true", "limit": 100}, retry_limit=0, headers=self._headers,
        )
        data = self._run_data(response)
        matches: list[dict[str, Any]] = []
        for candidate in data.get("items", []):
            if not isinstance(candidate, dict) or candidate.get("buildNumber") != spec.build:
                continue
            try:
                timestamp = datetime.fromisoformat(str(candidate.get("startedAt", "")).replace("Z", "+00:00"))
                age = (timestamp.astimezone(UTC) - started_at.astimezone(UTC)).total_seconds()
            except (ValueError, TypeError):
                continue
            store_id = candidate.get("defaultKeyValueStoreId")
            if not -5 <= age <= 120 or not store_id:
                continue
            original = await self._get(
                f"{self.base_url}/key-value-stores/{store_id}/records/INPUT", retry_limit=0, headers=self._headers,
            )
            if original.json() == actor_input:
                matches.append(candidate)
        return matches[0] if len(matches) == 1 else None

    async def _finish_execution(
        self, call: PlannedToolCall, started_data: dict[str, Any], *, monitoring: bool,
    ) -> ApifyExecutionResult:
        spec = self.registry.require(call.capability)
        timeout_error = None
        failed_error = None
        try:
            run_data = await self._wait_for_terminal(started_data)
        except ApifyActorFailedError as error:
            if monitoring and error.status == "ABORTED" and error.run_data:
                run_data = error.run_data
                timeout_error = ApifyTimeoutError("Execução interrompida com aborto terminal confirmado; dados independentes recuperados do dataset.", run_id=error.run_id, run_data=run_data)
            else:
                if not error.run_data or not error.run_data.get("defaultDatasetId"):
                    if error.run_data and not monitoring:
                        error.run_data = await self._reconcile_billing(error.run_data)
                    raise
                # A failed Actor can still have produced paid output. Archive
                # it while retaining the terminal failure as the result.
                run_data = error.run_data
                failed_error = error
        except ApifySchemaDriftError as error:
            raise ApifyReconciliationRequiredError(
                "Metadados remotos incompletos; requer reconciliação da run existente.",
                run_data=started_data,
            ) from error
        except httpx.HTTPError as error:
            raise ApifyReconciliationRequiredError(
                "Acompanhamento remoto interrompido; requer reconciliação da run existente.",
                run_data=started_data,
            ) from error
        except asyncio.CancelledError:
            if started_data.get("id") and started_data.get("status") != "SUCCEEDED":
                with suppress(httpx.HTTPError):
                    await self._client.post(
                        f"{self.base_url}/actor-runs/{started_data['id']}/abort",
                        headers=self._headers,
                    )
            raise
        except ApifyTimeoutError as exc:
            if not exc.run_data or exc.run_data.get("status") != "ABORTED":
                raise ApifyReconciliationRequiredError(
                    f"{exc} Aborto não confirmado; requer reconciliação antes de nova coleta.",
                    run_data=exc.run_data or started_data,
                ) from exc
            # The stopped actor may have persisted independently completed items.
            # They still pass the same pinned-build, schema and evidence gates.
            timeout_error = exc
            run_data = exc.run_data

        try:
            run_data = await self._resolve_missing_build(run_data)
        except (httpx.HTTPError, ApifySchemaDriftError) as error:
            raise ApifyReconciliationRequiredError(
                "Identidade do build remoto sem confirmação; requer reconciliação.",
                run_data=run_data,
            ) from error
        if not monitoring:
            run_data = await self._reconcile_billing(run_data)
        if timeout_error is not None:
            timeout_error.run_data = run_data

        run_id = str(run_data.get("id", ""))
        dataset_id = str(run_data.get("defaultDatasetId", ""))
        build_number = str(run_data.get("buildNumber") or "")
        if not run_id or not dataset_id or not build_number:
            raise ApifySchemaDriftError(
                "A run concluída não contém run id, dataset id e build number.",
                run_data=run_data,
            )
        if build_number != spec.build:
            raise ApifySchemaDriftError(
                f"A run usou build {build_number}, diferente do build pinado {spec.build}.",
                run_data=run_data,
            )

        # The scope belongs to the Actor input. Once paid output exists, retrieve
        # every row, including hidden fields and diagnostic records. A local
        # analysis sample must never discard the remainder of a produced dataset.
        items: list[dict[str, Any]] = []
        offset = 0
        reported_total: int | None = None
        page_size = 1000

        def pending_terminal_collection() -> ApifyActorFailedError | ApifyTimeoutError:
            error = failed_error or timeout_error
            assert error is not None
            error.run_data = run_data
            error.dataset_read_pending = True
            error.dataset_result = ApifyExecutionResult(
                run=ApifyRunMetadata(
                    run_id=run_id, dataset_id=dataset_id, status=str(run_data["status"]),
                    actor_id=spec.actor_id, build_number=build_number,
                    incomplete_reason="dataset_read_pending",
                ),
                items=items,
                total_items=reported_total if reported_total is not None else len(items),
                total_items_source="unverified",
            )
            return error

        while True:
            current_limit = min(page_size, reported_total - offset) if reported_total is not None else page_size
            try:
                items_response = await self._get(
                    f"{self.base_url}/datasets/{dataset_id}/items",
                    params={
                        "format": "json",
                        "clean": "false",
                        "limit": current_limit,
                        "offset": offset,
                    },
                    headers=self._headers,
                )
                items_response.raise_for_status()
                page_data = items_response.json()
                total_header = items_response.headers.get("X-Apify-Pagination-Total")
                if total_header is not None:
                    try:
                        page_total = int(total_header)
                    except ValueError as error:
                        raise ApifyReconciliationRequiredError(
                            "Contagem de paginação inválida; reconciliar o dataset existente.", run_data=run_data,
                        ) from error
                    if page_total < 0 or (reported_total is not None and page_total != reported_total):
                        raise ApifyReconciliationRequiredError(
                            "Contagem do dataset mudou durante a leitura; reconciliar a mesma run.", run_data=run_data,
                        )
                    reported_total = page_total
                if not isinstance(page_data, list):
                    raise ValueError("Dataset não retornou uma lista JSON.")
                if any(not isinstance(item, dict) for item in page_data):
                    raise ValueError("Dataset contém item que não é um objeto JSON.")
                items.extend(page_data)
                offset += len(page_data)
                if reported_total is not None:
                    if offset > reported_total or (len(page_data) < current_limit and offset < reported_total):
                        raise ApifyReconciliationRequiredError(
                            "Dataset retornou página incompleta ou contagem divergente; reconciliar a mesma run.", run_data=run_data,
                        )
                    if offset == reported_total:
                        break
                elif len(page_data) < current_limit:
                    break
            except ApifyReconciliationRequiredError as exc:
                if failed_error is not None or timeout_error is not None:
                    raise pending_terminal_collection() from exc
                raise
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                if failed_error is not None or timeout_error is not None:
                    raise pending_terminal_collection() from exc
                if isinstance(exc, httpx.HTTPError):
                    raise ApifyReconciliationRequiredError(
                        "Leitura do dataset pago interrompida; requer reconciliação da run existente.",
                        run_data=run_data,
                    ) from exc
                raise ApifySchemaDriftError(str(exc), run_data=run_data) from exc

        total_items = reported_total if reported_total is not None else len(items)

        raw_cost = run_data.get("usageTotalUsd")
        cost_usd = float(raw_cost) if isinstance(raw_cost, int | float) and not isinstance(raw_cost, bool) and math.isfinite(raw_cost) and raw_cost >= 0 else 0.0

        result = ApifyExecutionResult(
            run=ApifyRunMetadata(
                run_id=run_id,
                dataset_id=dataset_id,
                status=str(run_data["status"]),
                actor_id=spec.actor_id,
                build_number=build_number,
                cost_usd=round(cost_usd, 6),
                cost_status="observed_provisional" if isinstance(raw_cost, int | float) and not isinstance(raw_cost, bool) and math.isfinite(raw_cost) and raw_cost >= 0 else "pending",
                incomplete_reason=str(timeout_error) if timeout_error else None,
            ),
            items=items,
            total_items=total_items,
            total_items_source="provider_pagination" if reported_total is not None else "terminal_exhaustion",
        )
        if failed_error is not None:
            failed_error.run_data = run_data
            failed_error.dataset_result = result
            raise failed_error
        if timeout_error is not None and not items:
            timeout_error.run_data = run_data
            timeout_error.dataset_result = result
            raise timeout_error
        try:
            validate_dataset_items(call.capability, items)
        except ValueError as error:
            # Preserve paid records for private audit without admitting an
            # unknown schema as analytical evidence.
            raise ApifySchemaDriftError(
                str(error), run_data=run_data, dataset_result=result,
            ) from error
        return result

    async def aclose(self) -> None:
        if self._owns_client or not self._client.is_closed:
            await self._client.aclose()


class ApifyCollector(MarketSourcePort):
    """Compatibilidade temporária para o port antigo, sem fallback ou Actor implícito."""

    def __init__(
        self,
        api_token: str | None = None,
        base_url: str = "https://api.apify.com/v2",
        timeout_seconds: float = 30.0,
        polling_interval_seconds: float = 0.5,
        max_poll_attempts: int = 120,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = AppSettings()
        self._settings = settings
        self._client = ApifyClient(
            api_token=api_token or settings.APIFY_TOKEN,
            registry=ApifyActorRegistry.from_settings(settings),
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            polling_interval_seconds=polling_interval_seconds,
            max_poll_attempts=max_poll_attempts,
            http_client=http_client,
        )

    async def collect(
        self,
        analysis_id: str,
        search_terms: list[str],
        plan: ResearchPlan | None = None,
    ) -> list[MarketEvidence]:
        evidences: list[MarketEvidence] = []
        for index, term in enumerate(search_terms):
            remaining_budget = (
                plan.budget_limit_usd - plan.spent_usd
                if plan is not None
                else self._settings.APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS
            )
            if remaining_budget is not None and remaining_budget <= 0:
                raise ApifyBudgetExceededError("Orçamento da análise esgotado.")
            call = PlannedToolCall(
                id=f"legacy-google-search-{index}",
                capability="google_search",
                query=term,
                required=True,
                rationale="Compatibilidade temporária do coletor antigo.",
                max_items=20,
                parameters={"country": "BR", "language": "pt"},
            )
            result = await self._client.execute(
                call,
                max_total_charge_usd=remaining_budget,
            )
            if plan is not None:
                plan.record_cost(result.run.cost_usd)
            evidences.append(
                MarketEvidence.create(
                    analysis_id=analysis_id,
                    evidence_type=self._client.registry.require("google_search").evidence_type,
                    source_name="apify_google_search",
                    source_url=f"https://www.google.com/search?q={quote_plus(term)}",
                    collector="apify_actor_runner",
                    title=f"Pesquisa Google: {term}",
                    raw_payload={
                        "run_id": result.run.run_id,
                        "dataset_id": result.run.dataset_id,
                        "actor_id": result.run.actor_id,
                        "build_number": result.run.build_number,
                        "query": term,
                        "total_items": result.total_items,
                        "items": result.items,
                    },
                    cost_usd=result.run.cost_usd,
                )
            )
        return evidences


class FakeApifyCollector(MarketSourcePort):
    """Test double explícito; nunca é criado pelas factories de runtime."""

    def __init__(
        self,
        canned_jobs: list[dict[str, Any]] | None = None,
        cost_per_term: float = 0.05,
        simulate_error: bool = False,
    ) -> None:
        self.canned_jobs = canned_jobs
        self.cost_per_term = cost_per_term
        self.simulate_error = simulate_error
        self.call_count = 0

    async def collect(
        self,
        analysis_id: str,
        search_terms: list[str],
        plan: ResearchPlan | None = None,
    ) -> list[MarketEvidence]:
        if self.simulate_error:
            raise ApifyError("Erro simulado na API do Apify (Timeout / 502)")

        evidences: list[MarketEvidence] = []
        for term in search_terms:
            if plan and not plan.has_budget_for(self.cost_per_term):
                break
            self.call_count += 1
            if plan:
                plan.record_cost(self.cost_per_term)
            items = self.canned_jobs or [
                {
                    "title": f"Analista de {term}",
                    "company": "Empresa de teste",
                    "location": "São Paulo, SP",
                }
            ]
            evidences.append(
                MarketEvidence.create(
                    analysis_id=analysis_id,
                    evidence_type=EvidenceType.JOB_MARKET,
                    source_name="test_double_apify_jobs",
                    source_url="https://example.invalid/test-only",
                    collector="fake_apify_collector",
                    title=f"Fixture de teste: {term}",
                    raw_payload={"term": term, "items": items},
                    cost_usd=self.cost_per_term,
                )
            )
        return evidences
