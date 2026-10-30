"""Cliente Apify assíncrono com Actors pinados, orçamento e proveniência real."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote_plus

import httpx

from prometeus.application.tool_capabilities import CAPABILITY_LIMIT_UNITS
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
        super().__init__(message)


class ApifySchemaDriftError(ApifyError):
    """Resposta da Apify ou dataset divergiu do contrato esperado."""

    def __init__(self, message: str, *, run_data: dict[str, Any] | None = None) -> None:
        self.run_data = run_data
        super().__init__(message)


class ApifyActorFailedError(ApifyError):
    """A run terminou em um estado de falha explícito."""

    def __init__(self, *, run_id: str, status: str, message: str = "") -> None:
        self.run_id = run_id
        self.status = status
        safe_message = message.strip().replace("\r", " ").replace("\n", " ")[:500]
        detail = f": {safe_message}" if safe_message else ""
        super().__init__(f"Run Apify {run_id} terminou com status {status}{detail}")


TERMINAL_STATUSES = frozenset(
    {"SUCCEEDED", "FAILED", "TIMING-OUT", "TIMED-OUT", "ABORTING", "ABORTED"}
)
FAILED_STATUSES = TERMINAL_STATUSES - {"SUCCEEDED"}


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

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_token}",
        }

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
            await asyncio.sleep(self.polling_interval_seconds)
            response = await self._client.get(poll_url, headers=self._headers)
            response.raise_for_status()
            run_data = self._run_data(response)
            self._ensure_success_or_raise(run_data)
            if run_data.get("status") == "SUCCEEDED":
                return run_data
        # A local timeout must not leave a paid Actor running indefinitely.
        cancellation = "Cancelamento remoto não confirmado; requer reconciliação."
        terminal_data = None
        try:
            aborted = await self._client.post(f"{poll_url}/abort", headers=self._headers)
            aborted.raise_for_status()
            abort_data = self._run_data(aborted)
            if abort_data.get("status") in {"ABORTED", "ABORTING"}:
                cancellation = "Cancelamento remoto confirmado."
            if abort_data.get("status") == "ABORTED":
                terminal_data = abort_data
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
            response = await self._client.get(
                f"{self.base_url}/actor-runs/{run_id}", headers=self._headers
            )
            response.raise_for_status()
            refreshed = self._run_data(response)
            if refreshed.get("id") != run_id or refreshed.get("status") not in {
                "SUCCEEDED",
                "ABORTED",
            }:
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
                response = await self._client.get(
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

    async def execute(
        self,
        call: PlannedToolCall,
        *,
        max_total_charge_usd: float,
    ) -> ApifyExecutionResult:
        if max_total_charge_usd <= 0:
            raise ApifyBudgetExceededError("A chamada Apify não possui orçamento positivo.")

        spec = self.registry.require(call.capability)
        actor_input = self.registry.build_input(call)
        start_url = f"{self.base_url}/actors/{spec.actor_path}/runs"
        response = await self._client.post(
            start_url,
            params={
                "build": spec.build,
                "waitForFinish": self.wait_for_finish_seconds,
                "maxItems": call.max_items,
                "maxTotalChargeUsd": max_total_charge_usd,
                "restartOnError": "false",
            },
            json=actor_input,
            headers=self._headers,
        )
        response.raise_for_status()
        timeout_error = None
        try:
            run_data = await self._wait_for_terminal(self._run_data(response))
        except ApifyTimeoutError as exc:
            if not exc.run_data or exc.run_data.get("status") != "ABORTED":
                raise
            # The stopped actor may have persisted independently completed items.
            # They still pass the same pinned-build, schema and evidence gates.
            timeout_error = exc
            run_data = exc.run_data

        run_data = await self._resolve_missing_build(run_data)

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

        fetch_limit = call.max_items
        limit_unit = getattr(spec, "limit_unit", None) or CAPABILITY_LIMIT_UNITS.get(call.capability)
        if limit_unit == "per_video" or call.capability == "youtube_comments":
            urls = call.parameters.get("urls", call.parameters.get("start_urls", []))
            num_urls = len(urls) if isinstance(urls, list) and urls else 1
            fetch_limit = max(call.max_items, num_urls * call.max_items)

        items: list[dict[str, Any]] = []
        offset = 0
        total_items = 0
        page_size = min(fetch_limit, 1000)

        while len(items) < fetch_limit:
            current_limit = min(page_size, fetch_limit - len(items))
            try:
                items_response = await self._client.get(
                    f"{self.base_url}/datasets/{dataset_id}/items",
                    params={
                        "format": "json",
                        "clean": "true",
                        "limit": current_limit,
                        "offset": offset,
                    },
                    headers=self._headers,
                )
                items_response.raise_for_status()
                page_data = items_response.json()
                if not isinstance(page_data, list) or not page_data:
                    break
                page_items = validate_dataset_items(call.capability, page_data)
                items.extend(page_items)
                offset += len(page_data)

                total_header = items_response.headers.get("X-Apify-Pagination-Total")
                if total_header is not None:
                    try:
                        total_items = int(total_header)
                    except ValueError:
                        total_items = max(total_items, len(items))
                else:
                    total_items = max(total_items, len(items))

                if len(page_data) < current_limit or (total_items and offset >= total_items):
                    break
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                if timeout_error is not None:
                    raise timeout_error from exc
                if isinstance(exc, httpx.HTTPError):
                    raise
                raise ApifySchemaDriftError(str(exc), run_data=run_data) from exc

        if not total_items:
            total_items = len(items)

        if timeout_error is not None and not items:
            raise timeout_error

        raw_cost = run_data.get("usageTotalUsd", 0.0)
        cost_usd = float(raw_cost) if isinstance(raw_cost, int | float) else 0.0

        return ApifyExecutionResult(
            run=ApifyRunMetadata(
                run_id=run_id,
                dataset_id=dataset_id,
                status=str(run_data["status"]),
                actor_id=spec.actor_id,
                build_number=build_number,
                cost_usd=round(cost_usd, 6),
                incomplete_reason=str(timeout_error) if timeout_error else None,
            ),
            items=items,
            total_items=total_items,
        )

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
            if remaining_budget <= 0:
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
