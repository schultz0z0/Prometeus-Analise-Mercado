"""Cliente HTTP e adaptador oficial para as APIs institucionais da ENS."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from prometeus.domain.ports.institutional_data import (
    AdapterHealthStatus,
    CanonicalCourse,
    FinancialMetrics,
    FunnelMetrics,
    InstitutionalDataAdapter,
)
from prometeus.infrastructure.institutional.ens.mappers import (
    consolidate_funnel_metrics,
    map_ens_course,
    map_ens_inscritos,
    map_ens_leads,
    map_ens_matriculados,
)

logger = logging.getLogger(__name__)


class ENSError(Exception):
    """Exceção base para falhas de comunicação com a ENS."""

    pass


class ENSAuthenticationError(ENSError):
    """Token expirado ou credencial inválida."""

    pass


class ENSInstitutionalAdapter(InstitutionalDataAdapter):
    """Adaptador de produção para as APIs de Leads, Inscritos e Matriculados da ENS."""

    def __init__(
        self,
        base_url: str = "https://api.ens.edu.br/v1",
        api_token: str = "",
        timeout_seconds: float = 20.0,
        max_retries: int = 3,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._custom_client = http_client

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Prometeus-Engine/1.0 (+https://prometeus.agenciaprometeus.com.br)",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def _safe_get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Executa requisição GET segura com retries exponenciais para 429 e 5xx."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        client = self._custom_client or httpx.AsyncClient(timeout=self.timeout_seconds)
        close_client = self._custom_client is None

        try:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code == 401:
                        raise ENSAuthenticationError(
                            "Credencial não autorizada para as APIs da ENS."
                        )
                    if response.status_code in {429, 500, 502, 503, 504}:
                        if attempt == self.max_retries:
                            response.raise_for_status()
                        delay = 0.5 * (2 ** (attempt - 1))
                        logger.warning(
                            f"Tentativa {attempt} falhou ({response.status_code}). Aguardando {delay}s..."
                        )
                        await asyncio.sleep(delay)
                        continue

                    response.raise_for_status()
                    result: Any = response.json()
                    if isinstance(result, dict):
                        return result
                    return {"data": result}
                except (httpx.TransportError, httpx.TimeoutException) as exc:
                    if attempt == self.max_retries:
                        raise ENSError(f"Erro de transporte conectando à ENS: {exc}") from exc
                    delay = 0.5 * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

            raise ENSError("Número máximo de retentativas excedido sem sucesso.")
        finally:
            if close_client:
                await client.aclose()

    async def list_courses(
        self,
        query: str | None = None,
        category: str | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> list[CanonicalCourse]:
        params: dict[str, Any] = {"page": page, "per_page": limit}
        if query:
            params["q"] = query
        if category:
            params["categoria"] = category

        payload = await self._safe_get("cursos", params=params)
        raw_items = payload.get("data") or payload.get("items") or []
        return [map_ens_course(item) for item in raw_items]

    async def get_course(self, course_id: str) -> CanonicalCourse | None:
        try:
            payload = await self._safe_get(f"cursos/{course_id}")
            raw = payload.get("data") or payload
            return map_ens_course(raw)
        except Exception as exc:
            logger.warning(f"Não foi possível recuperar curso {course_id}: {exc}")
            return None

    async def get_funnel_metrics(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FunnelMetrics]:
        # Busca em paralelo dos 3 endpoints: leads, inscritos e matriculados
        params = {}
        if period:
            params["periodo"] = period

        leads_task = self._safe_get("leads", params=params)
        inscritos_task = self._safe_get("inscritos", params=params)
        matriculados_task = self._safe_get("matriculados", params=params)

        leads_raw, inscritos_raw, matriculados_raw = await asyncio.gather(
            leads_task, inscritos_task, matriculados_task
        )

        leads_list = leads_raw.get("data") or leads_raw.get("items") or []
        inscritos_list = inscritos_raw.get("items") or inscritos_raw.get("data") or []
        matriculados_list = matriculados_raw.get("registros") or matriculados_raw.get("data") or []

        leads_map = map_ens_leads(leads_list)
        inscritos_map = map_ens_inscritos(inscritos_list)
        matriculados_map, _ = map_ens_matriculados(matriculados_list)

        funnel_list, quality_score, warnings = consolidate_funnel_metrics(
            course_ids=course_ids,
            leads_map=leads_map,
            inscritos_map=inscritos_map,
            matriculados_map=matriculados_map,
            period=period,
        )
        logger.info(
            f"Métricas consolidadas para {len(funnel_list)} registros. Quality Score: {quality_score}"
        )
        return funnel_list

    async def get_financial_metrics(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FinancialMetrics]:
        params = {}
        if period:
            params["semestre"] = period

        matriculados_raw = await self._safe_get("matriculados", params=params)
        matriculados_list = matriculados_raw.get("registros") or matriculados_raw.get("data") or []
        _, financial_map = map_ens_matriculados(matriculados_list)

        results: list[FinancialMetrics] = []
        for (cid, per), fin in financial_map.items():
            if course_ids and cid not in course_ids:
                continue
            if period and per != period:
                continue
            results.append(fin)
        return results

    async def healthcheck(self) -> AdapterHealthStatus:
        start_time = time.perf_counter()
        try:
            await self._safe_get("health")
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return AdapterHealthStatus(
                status="ok",
                adapter_name="ens",
                latency_ms=round(elapsed, 2),
                message="Conexão com a ENS estabelecida com sucesso",
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return AdapterHealthStatus(
                status="error",
                adapter_name="ens",
                latency_ms=round(elapsed, 2),
                message=f"Falha ao conectar com endpoint da ENS: {exc}",
            )
